"""
核心记忆库管理系统

提供记忆的存储、检索、更新和删除功能
"""
from typing import List, Optional, Dict, Tuple, Any
from pathlib import Path
import os
import numpy as np
import json
from dataclasses import dataclass

from datetime import datetime

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
        summary: 针对于检索关键词的记忆摘要
    """
    summary: str


class MemoryBank:
    """
    记忆库管理类
    
    提供记忆的增删改查、向量检索、权重衰减等功能
    """
    
    def __init__(
        self,
        path: Optional[str] = None,
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
        
        # 设置记忆库路径
        if path is None:
            path_config = load_path_config()
            self.path = path_config.MEMORYBANK_PATH / 'memory_bank.json'
        
        # 确保目录存在
        if not self.path.exists():
            os.makedirs(self.path.parent, exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump([], f, indent=4)
        
        # 缓存所有记忆
        self._memory_cache: Dict[str, Memory] = {}
        self._load_memories()
        
        self._reranker_model: Optional[RerankerModel] = None
    
    def _load_memories(self) -> None:
        """从记忆库加载所有记忆到缓存"""
        try:
            with open(self.path, 'r') as f:
                memories = json.load(f)
            for memory in memories:
                self._memory_cache[memory['id']] = Memory(**memory)
        except FileNotFoundError:
            pass
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
    ) -> str:
        """
        添加记忆到记忆库
        
        Args:
            memory: 要添加的记忆对象
            generate_vector: 是否生成向量（None则使用配置）
            
        Returns:
            添加的记忆ID
        """
        memory.update_text_content()
        try:
            self._memory_cache[memory.id] = memory
            return memory.id
        finally:
            self._save_memories()   
    def _save_memories(self) -> None:
        """将缓存中的记忆保存到文件"""
        with open(self.path, 'w') as f:
            json.dump(
                [memory.model_dump() for memory in self._memory_cache.values()],
                f,
                indent=4,
                ensure_ascii=False
            )
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
        
        self._save_memories()

    def search(
        self,
        query: str,
        top_k: int = 10,
        depth: int = 0
    ) -> MemorySearchResult:
        """
        搜索记忆
        
        搜索流程：
        1. 重排序（_rerank_search）
        2. 模型抽取总结
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
            depth: 搜索深度
                - 0: 只检索关键词匹配的记忆
                - 1: 继续检索第一轮匹配记忆的关联记忆
            
        Returns:
            匹配的记忆搜索结果列表，按相关性从高到低排序
        """
        if not self._memory_cache:
            return MemorySearchResult('')
        
        # 重排序
        texts = []
        ids = []
        for memory in self._memory_cache.values():
            texts.append(memory.text_content)
            ids.append(memory.id)
        
        results = self.reranker_model.rerank(
                query=query,
                documents=texts,
                top_k=top_k
            )
            
        candidate_ids = []
        for result in results:
            idx = result['index']
            mid = ids[idx]
            candidate_ids.append(mid)
        
        # 扩展候选记忆
        expanded_ids = self._expand_candidates(candidate_ids, depth)
        text_to_summary = '\n'.join([self._memory_cache[mid].text_content for mid in expanded_ids])
        # 调用摘要模型
        summary = self.summary_model.generate_summary(
            text=text_to_summary,
            query=query
        )
        return MemorySearchResult(summary)


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
    
    def _generate_summary(self, text: str, query: str) -> str:
        """
        生成记忆摘要
        
        Args:
            text: 记忆文本内容
            query: 搜索查询
            
        Returns:
            摘要文本
        """
        try:
            # 加载摘要提示词
            prompt = self._load_summary_prompt()
            prompt.format(text=text, query=query)    
            
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
    path: Optional[str] = None,
    config: Optional[MemoryBankConfig] = None
) -> MemoryBank:
    """
    加载记忆库实例（单例模式）
    
    Args:
        path: 记忆库路径
        config: 记忆库配置
        
    Returns:
        MemoryBank 实例
    """
    global _memory_bank_instance
    
    if _memory_bank_instance is None:
        _memory_bank_instance = MemoryBank(path=path, config=config)
    
    return _memory_bank_instance


def get_memory_bank() -> Optional[MemoryBank]:
    """
    获取已加载的记忆库实例
    
    Returns:
        MemoryBank 实例，如果未加载返回 None
    """
    return _memory_bank_instance
