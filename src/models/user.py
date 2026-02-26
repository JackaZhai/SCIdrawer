"""
用户模型
"""

import base64
import os
from datetime import datetime
from hashlib import pbkdf2_hmac
from typing import Dict, Optional

from .base import BaseModel


class User(BaseModel):
    """用户模型类"""

    def __init__(
        self,
        id: Optional[int] = None,
        username: str = "",
        salt: bytes = b"",
        password_hash: str = "",
        created_at: Optional[str] = None,
    ):
        self.id = id
        self.username = username
        self.salt = salt
        self.password_hash = password_hash
        self.created_at = created_at or datetime.utcnow().isoformat()

    @classmethod
    def get_table_name(cls) -> str:
        return "users"

    @classmethod
    def get_create_table_sql(cls) -> str:
        return """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            salt BLOB NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(
            id=row["id"],
            username=row["username"],
            salt=row["salt"],
            password_hash=row["password_hash"],
            created_at=row["created_at"],
        )

    def to_dict(self) -> Dict:
        return {"id": self.id, "username": self.username, "created_at": self.created_at}

    @staticmethod
    def generate_salt() -> bytes:
        """生成随机盐"""
        return os.urandom(16)

    @staticmethod
    def hash_password(password: str, salt: bytes) -> str:
        """哈希密码"""
        digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return base64.b64encode(digest).decode("utf-8")

    def set_password(self, password: str) -> None:
        """设置密码"""
        self.salt = self.generate_salt()
        self.password_hash = self.hash_password(password, self.salt)

    def verify_password(self, password: str) -> bool:
        """验证密码"""
        if not self.salt or not self.password_hash:
            return False
        return self.hash_password(password, self.salt) == self.password_hash

    @classmethod
    def get_by_username(cls, username: str) -> Optional["User"]:
        """根据用户名获取用户"""
        from ..services.database import get_db_manager

        db = get_db_manager()
        row = db.fetch_one("SELECT * FROM users WHERE username = ?", (username,))
        return cls.from_row(row) if row else None

    def save(self) -> None:
        """保存用户到数据库"""
        from ..services.database import get_db_manager

        db = get_db_manager()

        if self.id is None:
            # 插入新用户
            cursor = db.execute_query(
                "INSERT INTO users (username, salt, password_hash) VALUES (?, ?, ?) RETURNING id",
                (self.username, self.salt, self.password_hash),
            )
            self.id = cursor.fetchone()["id"]
        else:
            # 更新现有用户
            db.execute_query(
                "UPDATE users SET username = ?, salt = ?, password_hash = ? WHERE id = ?",
                (self.username, self.salt, self.password_hash, self.id),
            )

    @classmethod
    def create_default_user(cls, username: str, password: str) -> "User":
        """创建默认用户"""
        user = cls(username=username)
        user.set_password(password)
        user.save()
        return user

    @classmethod
    def ensure_default_user(
        cls, username: Optional[str] = None, password: Optional[str] = None
    ) -> "User":
        """确保默认用户存在"""
        from ..config import Config

        config = Config()

        default_username = username or config.seed_username
        default_password = password or config.seed_password

        user = cls.get_by_username(default_username)
        if not user:
            user = cls.create_default_user(default_username, default_password)
        return user
