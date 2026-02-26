"""
基础模型类
"""

import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Dict, Type, TypeVar

T = TypeVar("T", bound="BaseModel")


class BaseModel(ABC):
    """所有模型的基础类"""

    @classmethod
    @abstractmethod
    def get_table_name(cls) -> str:
        """获取表名"""
        pass

    @classmethod
    @abstractmethod
    def get_create_table_sql(cls) -> str:
        """获取创建表的SQL语句"""
        pass

    @classmethod
    def init_table(cls, conn: sqlite3.Connection) -> None:
        """初始化表"""
        conn.execute(cls.get_create_table_sql())

    @classmethod
    def from_row(cls: Type[T], row: sqlite3.Row) -> T:
        """从数据库行创建模型实例"""
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        raise NotImplementedError
