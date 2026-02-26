"""
使用统计模型
"""

from datetime import datetime
from typing import Dict, Optional

from .base import BaseModel


class UsageStats(BaseModel):
    """使用统计模型类"""

    def __init__(
        self,
        user_id: Optional[int] = None,
        total_calls: int = 0,
        last_used_at: Optional[str] = None,
    ):
        self.user_id = user_id
        self.total_calls = total_calls
        self.last_used_at = last_used_at

    @classmethod
    def get_table_name(cls) -> str:
        return "usage_stats"

    @classmethod
    def get_create_table_sql(cls) -> str:
        return """
        CREATE TABLE IF NOT EXISTS usage_stats (
            user_id INTEGER PRIMARY KEY,
            total_calls INTEGER DEFAULT 0,
            last_used_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """

    @classmethod
    def from_row(cls, row) -> "UsageStats":
        return cls(
            user_id=row["user_id"], total_calls=row["total_calls"], last_used_at=row["last_used_at"]
        )

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "total_calls": self.total_calls,
            "last_used_at": self.last_used_at,
        }

    @classmethod
    def get_by_user_id(cls, user_id: int) -> Optional["UsageStats"]:
        """根据用户ID获取使用统计"""
        from ..services.database import get_db_manager

        db = get_db_manager()
        row = db.fetch_one("SELECT * FROM usage_stats WHERE user_id = ?", (user_id,))
        return cls.from_row(row) if row else None

    def save(self) -> None:
        """保存使用统计到数据库"""
        from ..services.database import get_db_manager

        db = get_db_manager()

        db.execute_query(
            """
            INSERT INTO usage_stats (user_id, total_calls, last_used_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                total_calls = excluded.total_calls,
                last_used_at = excluded.last_used_at
            """,
            (self.user_id, self.total_calls, self.last_used_at),
        )

    def record_usage(self) -> None:
        """记录一次使用"""
        self.total_calls += 1
        self.last_used_at = datetime.utcnow().isoformat()
        self.save()

    @classmethod
    def record_usage_for_user(cls, user_id: int) -> None:
        """为用户记录一次使用"""
        stats = cls.get_by_user_id(user_id)
        if not stats:
            stats = cls(user_id=user_id, total_calls=0)
        stats.record_usage()
