"""
数据库连接管理
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

from ..models.api_key import ApiKey
from ..models.provider_config import ProviderConfig
from ..models.usage_stats import UsageStats
from ..models.user import User


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("DB_PATH", "data/app.db")
        self.data_dir = os.getenv("DATA_DIR", "data")
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

    @contextmanager
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（上下文管理器）"""
        self._ensure_data_dir()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def init_database(self) -> None:
        """初始化数据库表"""
        with self.get_connection() as conn:
            # 创建所有表
            User.init_table(conn)
            ApiKey.init_table(conn)
            UsageStats.init_table(conn)
            ProviderConfig.init_table(conn)
            conn.commit()

    def execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行查询"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor

    def execute_many(self, query: str, params_list: list) -> None:
        """执行多个参数相同的查询"""
        with self.get_connection() as conn:
            conn.executemany(query, params_list)
            conn.commit()

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """获取单条记录"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()

    def fetch_all(self, query: str, params: tuple = ()) -> list:
        """获取所有记录"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()


# 全局数据库管理器实例
db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例（单例模式）"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
        db_manager.init_database()
    return db_manager
