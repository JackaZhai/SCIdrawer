"""Provider model configuration (per-user, per-provider).

Stores default text/image model names used by PaperBanana generation.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from .base import BaseModel


@dataclass
class ProviderConfig(BaseModel):
    user_id: int
    provider: str
    text_model: str
    image_model: str
    updated_at: str

    def __init__(
        self,
        user_id: int,
        provider: str,
        text_model: str = "",
        image_model: str = "",
        updated_at: Optional[str] = None,
    ):
        self.user_id = int(user_id)
        self.provider = (provider or "grsai").strip().lower() or "grsai"
        self.text_model = text_model or ""
        self.image_model = image_model or ""
        self.updated_at = updated_at or datetime.utcnow().isoformat()

    @classmethod
    def get_table_name(cls) -> str:
        return "provider_configs"

    @classmethod
    def get_create_table_sql(cls) -> str:
        return """
        CREATE TABLE IF NOT EXISTS provider_configs (
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            text_model TEXT DEFAULT '',
            image_model TEXT DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, provider),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """

    @classmethod
    def init_table(cls, conn: sqlite3.Connection) -> None:
        conn.execute(cls.get_create_table_sql())

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ProviderConfig":
        return cls(
            user_id=row["user_id"],
            provider=row["provider"],
            text_model=row["text_model"],
            image_model=row["image_model"],
            updated_at=row["updated_at"],
        )

    def to_dict(self) -> Dict:
        return {
            "userId": self.user_id,
            "provider": self.provider,
            "textModel": self.text_model,
            "imageModel": self.image_model,
            "updatedAt": self.updated_at,
        }

    def save(self) -> None:
        from ..services.database import get_db_manager

        db = get_db_manager()
        db.execute_query(
            """
            INSERT INTO provider_configs (user_id, provider, text_model, image_model, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, provider) DO UPDATE SET
                text_model = excluded.text_model,
                image_model = excluded.image_model,
                updated_at = excluded.updated_at
            """,
            (self.user_id, self.provider, self.text_model, self.image_model, self.updated_at),
        )

    @classmethod
    def get_by_user_provider(cls, user_id: int, provider: str) -> Optional["ProviderConfig"]:
        from ..services.database import get_db_manager

        db = get_db_manager()
        row = db.fetch_one(
            "SELECT * FROM provider_configs WHERE user_id = ? AND provider = ?",
            (user_id, (provider or "grsai").strip().lower() or "grsai"),
        )
        return cls.from_row(row) if row else None
