"""
SQLAlchemy 数据库模型，用于记忆库的持久化存储
"""
from typing import Optional, List
from datetime import datetime
import uuid
import json

from sqlalchemy import Column, String, Float, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()


class MemoryModel(Base):
    """
    记忆数据库模型
    
    存储记忆的文本内容、向量数据、权重、关联记忆ID等信息
    """
    __tablename__ = 'memories'
    
    # 主键：UUID字符串
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 文本数据：存储记忆的完整文本内容（包括summary和messages）
    text_content = Column(Text, nullable=False)
    
    # 摘要：可选的记忆摘要
    summary = Column(Text, nullable=True)
    
    # 消息原始数据：JSON格式存储消息列表
    messages_json = Column(Text, nullable=True)
    
    # 向量数据：JSON格式存储向量数组
    vector_json = Column(Text, nullable=True)
    
    # 权重：记忆的重要程度
    weight = Column(Float, default=1.0, nullable=False)
    
    # 关联记忆ID列表：JSON格式存储UUID字符串列表
    related_memory_ids_json = Column(Text, default='[]', nullable=False)
    
    # 创建时间
    created_at = Column(String(20), default=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'), nullable=False)
    
    # 更新时间
    updated_at = Column(String(20), default=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'), onupdate=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    @property
    def related_memory_ids(self) -> List[str]:
        """获取关联记忆ID列表"""
        if self.related_memory_ids_json:
            return json.loads(self.related_memory_ids_json)
        return []
    
    @related_memory_ids.setter
    def related_memory_ids(self, value: List[str]):
        """设置关联记忆ID列表"""
        self.related_memory_ids_json = json.dumps(value)
    
    @property
    def vector(self) -> Optional[List[float]]:
        """获取向量数据"""
        if self.vector_json:
            return json.loads(self.vector_json)
        return None
    
    @vector.setter
    def vector(self, value: Optional[List[float]]):
        """设置向量数据"""
        if value is not None:
            self.vector_json = json.dumps(value)
        else:
            self.vector_json = None
    
    @property
    def messages_data(self) -> Optional[List[dict]]:
        """获取消息原始数据"""
        if self.messages_json:
            return json.loads(self.messages_json)
        return None
    
    @messages_data.setter
    def messages_data(self, value: Optional[List[dict]]):
        """设置消息原始数据"""
        if value is not None:
            self.messages_json = json.dumps(value, ensure_ascii=False)
        else:
            self.messages_json = None


def init_database(db_path: str) -> tuple:
    """
    初始化数据库
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        (engine, Session) 元组
    """
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session


def get_session(engine) -> Session:
    """
    获取数据库会话
    
    Args:
        engine: SQLAlchemy引擎
        
    Returns:
        数据库会话
    """
    Session = sessionmaker(bind=engine)
    return Session()
