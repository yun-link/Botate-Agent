"""
核心记忆库管理系统

提供记忆的存储、检索、更新和删除功能
"""
from typing import List, Optional, Dict, Tuple, Any
from pathlib import Path
import os
import numpy as np
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from .models import MemoryModel, init_database, get_session
from .memory import Memory
from config.config import MemoryBankConfig, load_path_config, load_memory_bank_config
from model.model import EmbeddingModel, RerankerModel, call
from model.message_schemas import Message
from prompt_utils import SystemPrompt, UserPrompt, Prompt


@dataclass
class MemorySearchResult:
    """
    记忆搜索结果
    
    Attributes:
        memory: 记忆对象
        score: 置信度分数 (0-1)
    """
    memory: Memory
    score: float


class MemoryBank:
    """
    记忆库管理类
    
    提供记忆的增删改查、向量检索、权重衰减等功能
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        config: Optional[MemoryBankConfig] = None
    ):
        """
        初始化记忆库
        
        Args:
            db_path: 数据库路径，如果不指定则使用默认路径
            config: 记忆库配置，如果不指定则使用默认配置
        """
        # 加载配置
        self.config = config or load_memory_bank_config()
        
        # 设置数据库路径
        if db_path is None:
            path_config = load_path_config()
            db_path = str(path_config.MEMORYBANK_PATH / 'memory_bank.db')
        
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 初始化数据库
        self.engine, self.SessionLocal = init_database(db_path)
        
        # 缓存所有记忆
        self._memory_cache: Dict[str, Memory] = {}
        self._load_memories()
        
        # 模型实例（延迟加载）
        self._embedding_model: Optional[EmbeddingModel] = None
        self._reranker_model: Optional[RerankerModel] = None
    
    def _load_memories(self) -> None:
        """从数据库加载所有记忆到缓存"""
        session = get_session(self.engine)
        try:
            memory_models = session.query(MemoryModel).all()
            for model in memory_models:
                memory = Memory.from_model(model)
                self._memory_cache[memory.id] = memory
        finally:
            session.close()
    
    @property
    def embedding_model(self) -> EmbeddingModel:
        """延迟加载嵌入模型"""
        if self._embedding_model is None:
            self._embedding_model = EmbeddingModel(
                model_name=self.config.EMBEDDING_MODEL.model_name
            )
        return self._embedding_model
    
    @property
    def reranker_model(self) -> RerankerModel:
        """延迟加载重排序模型"""
        if self._reranker_model is None:
            self._reranker_model = RerankerModel(
                model_name=self.config.RERANKER_MODEL.model_name
            )
        return self._reranker_model
    
    def add(
        self,
        memory: Memory,
        generate_summary: bool = True,
        generate_vector: bool = True
    ) -> str:
        """
        添加记忆到记忆库
        
        Args:
            memory: 要添加的记忆对象
            generate_summary: 是否生成摘要（None则使用配置）
            generate_vector: 是否生成向量（None则使用配置）
            
        Returns:
            添加的记忆ID
        """
        # 确定是否生成摘要
        memory.update_text_content()
        if generate_summary and self.config.ENABLE_GENERATE_SUMMARY and not memory.summary:
            memory.summary = self._generate_summary(memory.text_content)
        memory.update_text_content()
        # 确定是否生成向量
        if generate_vector and self.config.ENABLE_GENERATE_VECTOR and memory.vector is None:
            memory.vector = self._generate_vector(memory.text_content)
        
        # 保存到数据库
        session = get_session(self.engine)
        try:
            model = memory.to_model()
            session.add(model)
            session.commit()
            
            # 更新缓存
            self._memory_cache[memory.id] = memory
            
            return memory.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete(self, memory_id: str, depth: int = 0) -> List[str]:
        """
        删除记忆及其关联记忆
        
        Args:
            memory_id: 要删除的记忆ID
            depth: 删除深度
                - 0: 只删除目标记忆
                - 1: 删除目标记忆及其关联记忆
                - 2: 再删除上一层被删除记忆的关联记忆，以此类推
            
        Returns:
            被删除的记忆ID列表
        """
        deleted_ids: List[str] = []
        
        def _delete_recursive(current_id: str, current_depth: int):
            if current_id in deleted_ids:
                return
            
            if current_id not in self._memory_cache:
                return
            
            memory = self._memory_cache[current_id]
            related_ids = memory.related_memory_ids.copy()
            
            # 如果深度大于0，递归删除关联记忆
            if current_depth < depth:
                for related_id in related_ids:
                    _delete_recursive(related_id, current_depth + 1)
            
            # 删除当前记忆
            deleted_ids.append(current_id)
        
        # 开始递归删除
        _delete_recursive(memory_id, 0)
        
        # 从数据库删除
        session = get_session(self.engine)
        try:
            session.query(MemoryModel).filter(
                MemoryModel.id.in_(deleted_ids)
            ).delete(synchronize_session=False)
            session.commit()
            
            # 从缓存中移除
            for did in deleted_ids:
                self._memory_cache.pop(did, None)
            
            return deleted_ids
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def search(
        self,
        query: str,
        top_k: int = 10,
        depth: int = 0
    ) -> List[MemorySearchResult]:
        """
        搜索记忆
        
        搜索流程：
        1. 基础字符匹配检索（_char_search）- 一定会进行
        2. 向量相似度检索（_vector_search）- 如果启用且所有候选都有向量数据
        3. 重排序（_rerank_search）- 如果启用
        
        置信度计算：按权重占比求平均值
        - 只进行第一轮：第一轮分数占100%
        - 第一轮+第二轮：第一轮占20%，第二轮占80%
        - 第一轮+第二轮+第三轮：第一轮占10%，第二轮占30%，第三轮占60%
        - 跳过第二轮直接进行第三轮：第一轮占20%，第三轮占80%
        
        Args:
            query: 搜索关键词
            top_k: 返回结果数量
            depth: 搜索深度
                - 0: 只检索关键词匹配的记忆
                - 1: 继续检索第一轮匹配记忆的关联记忆
            
        Returns:
            匹配的记忆搜索结果列表，按相关性从高到低排序
        """
        if not self._memory_cache:
            return []
        
        # 第一轮：基础字符匹配（一定会进行）
        char_scores = self._char_search(query)
        
        # 收集所有候选记忆ID
        candidate_ids = set(char_scores.keys())
        
        # 如果深度大于0，扩展候选集
        if depth > 0:
            expanded_ids = self._expand_candidates(list(candidate_ids), depth)
            candidate_ids.update(expanded_ids)
            # 为扩展的记忆计算字符匹配分数
            for mid in expanded_ids:
                if mid not in char_scores:
                    char_scores[mid] = self._calculate_char_similarity(
                        query, self._memory_cache[mid].text_content
                    )
        
        # 初始化最终分数
        final_scores: Dict[str, float] = {}
        
        # 记录是否进行了向量搜索
        vector_search_done = False
        vector_scores: Dict[str, float] = {}
        
        # 第二轮：向量相似度检索
        if self.config.ENABLE_GENERATE_VECTOR:
            # 检查所有候选记忆是否都有向量数据
            all_have_vectors = all(
                self._memory_cache[mid].vector is not None
                for mid in candidate_ids
            )
            
            if all_have_vectors:
                vector_scores = self._vector_search(query, list(candidate_ids))
                vector_search_done = True
                
                # 第一轮占20%，第二轮占80%
                for mid in candidate_ids:
                    char_score = char_scores.get(mid, 0.0)
                    vector_score = vector_scores.get(mid, 0.0)
                    final_scores[mid] = char_score * 0.2 + vector_score * 0.8
            else:
                # 如果有记忆没有向量，直接使用第一轮分数（占100%）
                final_scores = char_scores.copy()
        else:
            # 如果未启用向量生成，直接使用第一轮分数（占100%）
            final_scores = char_scores.copy()
        
        # 第三轮：重排序
        if self.config.ENABLE_RERANK and len(final_scores) > 0:
            # 排序获取前50个候选
            sorted_candidates = sorted(
                final_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # 取前50个进行重排序
            rerank_candidates = sorted_candidates[:50]
            rerank_ids = [mid for mid, _ in rerank_candidates]
            rerank_scores = self._rerank_search(query, rerank_ids)
            
            # 计算最终分数
            combined_with_rerank: Dict[str, float] = {}
            for mid in rerank_ids:
                rerank_score = rerank_scores.get(mid, 0.0)
                
                if vector_search_done:
                    # 三轮都进行了：第一轮10%，第二轮30%，第三轮60%
                    char_score = char_scores.get(mid, 0.0)
                    vector_score = vector_scores.get(mid, 0.0)
                    combined_with_rerank[mid] = (
                        char_score * 0.1 + vector_score * 0.30 + rerank_score * 0.6
                    )
                else:
                    # 跳过了第二轮：第一轮20%，第三轮80%
                    char_score = char_scores.get(mid, 0.0)
                    combined_with_rerank[mid] = char_score * 0.2 + rerank_score * 0.8
            
            # 对于未参与重排序的候选，保留之前的分数
            for mid, score in sorted_candidates[50:]:
                combined_with_rerank[mid] = score
            
            final_scores = combined_with_rerank
        
        # 排序获取最终结果
        sorted_results = sorted(
            final_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # 返回top_k个记忆搜索结果
        result: List[MemorySearchResult] = []
        for mid, score in sorted_results[:top_k]:
            if mid in self._memory_cache:
                result.append(MemorySearchResult(
                    memory=self._memory_cache[mid],
                    score=score
                ))
        
        return result
    
    def _char_search(self, query: str) -> Dict[str, float]:
        """
        字符匹配检索
        
        Args:
            query: 搜索关键词
            
        Returns:
            记忆ID到匹配分数的映射
        """
        scores: Dict[str, float] = {}
        
        for memory_id, memory in self._memory_cache.items():
            score = self._calculate_char_similarity(query, memory.text_content)
            scores[memory_id] = score
        
        return scores
    
    def _calculate_char_similarity(self, query: str, text: str) -> float:
        """
        计算字符相似度
        
        使用简单的关键词匹配算法
        
        Args:
            query: 搜索查询
            text: 目标文本
            
        Returns:
            相似度分数 (0-1)
        """
        query_lower = query.lower()
        text_lower = text.lower()
        
        # 计算查询词在文本中出现的次数
        count = text_lower.count(query_lower)
        
        if count == 0:
            return 0.0
        
        # 归一化分数
        # 使用对数缩放避免分数过大
        import math
        score = min(1.0, math.log(count + 1) / 5)
        
        return score
    
    def _vector_search(
        self,
        query: str,
        candidate_ids: List[str]
    ) -> Dict[str, float]:
        """
        向量相似度检索
        
        Args:
            query: 搜索查询
            candidate_ids: 候选记忆ID列表
            
        Returns:
            记忆ID到向量相似度分数的映射
        """
        # 生成查询向量
        query_vector = self._generate_vector(query)
        
        if query_vector is None:
            return {}
        
        scores: Dict[str, float] = {}
        
        for mid in candidate_ids:
            memory = self._memory_cache.get(mid)
            if memory and memory.vector:
                similarity = self._cosine_similarity(query_vector, memory.vector)
                scores[mid] = similarity
        
        return scores
    
    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            余弦相似度
        """
        arr1 = np.array(vec1)
        arr2 = np.array(vec2)
        
        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def _rerank_search(
        self,
        query: str,
        candidate_ids: List[str]
    ) -> Dict[str, float]:
        """
        重排序检索
        
        Args:
            query: 搜索查询
            candidate_ids: 候选记忆ID列表
            
        Returns:
            记忆ID到重排序分数的映射
        """
        if not candidate_ids:
            return {}
        
        # 获取候选记忆的文本内容
        documents = []
        for mid in candidate_ids:
            memory = self._memory_cache.get(mid)
            if memory:
                documents.append(memory.text_content)
        
        if not documents:
            return {}
        
        # 调用重排序模型
        try:
            results = self.reranker_model.rerank(
                query=query,
                documents=documents,
                top_k=len(documents)
            )
            
            scores: Dict[str, float] = {}
            for result in results:
                idx = result['index']
                mid = candidate_ids[idx]
                scores[mid] = result['score']
            
            return scores
        except Exception as e:
            print(f"重排序失败: {e}")
            return {}
    
    def _expand_candidates(
        self,
        candidate_ids: List[str],
        depth: int
    ) -> set:
        """
        扩展候选记忆集合
        
        Args:
            candidate_ids: 初始候选记忆ID列表
            depth: 扩展深度
            
        Returns:
            扩展后的记忆ID集合
        """
        expanded = set()
        current_level = set(candidate_ids)
        
        for _ in range(depth):
            next_level = set()
            for mid in current_level:
                if mid in self._memory_cache:
                    memory = self._memory_cache[mid]
                    for related_id in memory.related_memory_ids:
                        if related_id not in expanded and related_id not in current_level:
                            next_level.add(related_id)
            
            expanded.update(next_level)
            current_level = next_level
            
            if not current_level:
                break
        
        return expanded
    
    def _generate_summary(self, text: str) -> str:
        """
        生成记忆摘要
        
        Args:
            text: 记忆文本内容
            
        Returns:
            摘要文本
        """
        try:
            # 加载摘要提示词
            prompt = self._load_summary_prompt()
            prompt.format(text=text)
            
            messages = [prompt.to_message()]
            
            summary = call(
                self.config.SUMMARY_MODEL.model_name,
                messages
            ).content.content

            return summary
        except Exception as e:
            print(f"生成摘要失败: {e}")
            return ""
    
    def _load_summary_prompt(self) -> UserPrompt:
        """加载摘要生成提示词"""
        path_config = load_path_config()
        prompt_path = path_config.PROMPTS_PATH / 'memory_summary_prompt.md'
        
        return UserPrompt.load_prompt_file(
            file_path=str(prompt_path)
        )
    
    def _generate_vector(self, text: str) -> Optional[List[float]]:
        """
        生成文本向量
        
        Args:
            text: 文本内容
            
        Returns:
            向量列表
        """
        try:
            vector = self.embedding_model.encode(text)
            return vector.tolist()
        except Exception as e:
            print(f"生成向量失败: {e}")
            return None
    
    def update_weight(self, memory_id: str, weight: float) -> bool:
        """
        更新记忆权重
        
        Args:
            memory_id: 记忆ID
            weight: 新权重
            
        Returns:
            是否成功
        """
        if memory_id not in self._memory_cache:
            return False
        
        memory = self._memory_cache[memory_id]
        memory.weight = weight
        memory.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        session = get_session(self.engine)
        try:
            model = session.query(MemoryModel).filter(
                MemoryModel.id == memory_id
            ).first()
            if model:
                model.weight = weight
                model.updated_at = memory.updated_at
                session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"更新权重失败: {e}")
            return False
        finally:
            session.close()
    
    def add_related_memory(
        self,
        memory_id: str,
        related_id: str
    ) -> bool:
        """
        添加关联记忆
        
        Args:
            memory_id: 主记忆ID
            related_id: 关联记忆ID
            
        Returns:
            是否成功
        """
        if memory_id not in self._memory_cache:
            return False
        if related_id not in self._memory_cache:
            return False
        
        memory = self._memory_cache[memory_id]
        if related_id not in memory.related_memory_ids:
            memory.related_memory_ids.append(related_id)
            memory.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            session = get_session(self.engine)
            try:
                model = session.query(MemoryModel).filter(
                    MemoryModel.id == memory_id
                ).first()
                if model:
                    model.related_memory_ids = memory.related_memory_ids
                    model.updated_at = memory.updated_at
                    session.commit()
                return True
            except Exception as e:
                session.rollback()
                print(f"添加关联记忆失败: {e}")
                return False
            finally:
                session.close()
        
        return True
    
    def weight_decay(self) -> None:
        """
        权重衰减
        
        对所有非重要记忆进行权重衰减
        """
        decay_rate = self.config.UPADATE_DECAY_WEIGHT
        important_weight = self.config.IMPROTANT_WEIGHT
        
        session = get_session(self.engine)
        try:
            for memory_id, memory in self._memory_cache.items():
                # 跳过重要记忆（权重为特殊值）
                if memory.weight == important_weight:
                    continue
                
                # 衰减权重
                new_weight = memory.weight * (1 - decay_rate)
                memory.weight = new_weight
                memory.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 更新数据库
                model = session.query(MemoryModel).filter(
                    MemoryModel.id == memory_id
                ).first()
                if model:
                    model.weight = new_weight
                    model.updated_at = memory.updated_at
            
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"权重衰减失败: {e}")
        finally:
            session.close()
    
    def forget_memories(self) -> List[str]:
        """
        遗忘记忆
        
        删除权重低于阈值的记忆（不包括重要记忆）
        
        Returns:
            被删除的记忆ID列表
        """
        threshold = self.config.FORGET_THRESHOLD_WEIGHT
        important_weight = self.config.IMPROTANT_WEIGHT
        
        to_forget = []
        for memory_id, memory in self._memory_cache.items():
            # 跳过重要记忆
            if memory.weight == important_weight:
                continue
            
            # 检查是否低于阈值
            if memory.weight < threshold:
                to_forget.append(memory_id)
        
        # 删除记忆
        deleted_ids = []
        for memory_id in to_forget:
            try:
                result = self.delete(memory_id, depth=0)
                deleted_ids.extend(result)
            except Exception as e:
                print(f"删除记忆 {memory_id} 失败: {e}")
        
        return deleted_ids
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """
        获取指定记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            记忆对象，如果不存在返回None
        """
        return self._memory_cache.get(memory_id)
    
    def get_all_memories(self) -> List[Memory]:
        """
        获取所有记忆
        
        Returns:
            所有记忆列表
        """
        return list(self._memory_cache.values())
    
    def count(self) -> int:
        """
        获取记忆总数
        
        Returns:
            记忆数量
        """
        return len(self._memory_cache)


# 全局记忆库实例
_memory_bank_instance: Optional[MemoryBank] = None


def load_memory_bank(
    db_path: Optional[str] = None,
    config: Optional[MemoryBankConfig] = None
) -> MemoryBank:
    """
    加载记忆库实例（单例模式）
    
    Args:
        db_path: 数据库路径
        config: 记忆库配置
        
    Returns:
        MemoryBank 实例
    """
    global _memory_bank_instance
    
    if _memory_bank_instance is None:
        _memory_bank_instance = MemoryBank(db_path=db_path, config=config)
    
    return _memory_bank_instance


def get_memory_bank() -> Optional[MemoryBank]:
    """
    获取已加载的记忆库实例
    
    Returns:
        MemoryBank 实例，如果未加载返回 None
    """
    return _memory_bank_instance
