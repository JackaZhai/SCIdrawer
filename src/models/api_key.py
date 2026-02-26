"""API key model (encrypted at rest).

Supports storing multiple keys per user, grouped by provider.
One active key is allowed per (user_id, provider).
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from .base import BaseModel


@dataclass
class ApiKey(BaseModel):
    id: str
    user_id: int
    provider: str
    value: str
    name: str
    base_url: str
    source: str
    is_active: bool
    created_at: str

    def __init__(
        self,
        id: Optional[str] = None,
        user_id: Optional[int] = None,
        provider: str = "grsai",
        value: str = "",
        name: str = "",
        base_url: str = "",
        source: str = "custom",
        is_active: bool = False,
        created_at: Optional[str] = None,
    ):
        self.id = id or uuid.uuid4().hex
        self.user_id = int(user_id) if user_id is not None else 0
        self.provider = (provider or "grsai").strip() or "grsai"
        self.value = value
        self.name = name or ""
        self.base_url = base_url or ""
        self.source = source or "custom"
        self.is_active = bool(is_active)
        self.created_at = created_at or datetime.utcnow().isoformat()

    @classmethod
    def get_table_name(cls) -> str:
        return "api_keys"

    @classmethod
    def get_create_table_sql(cls) -> str:
        return """
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL DEFAULT 'grsai',
            name TEXT DEFAULT '',
            base_url TEXT DEFAULT '',
            value TEXT NOT NULL,
            source TEXT DEFAULT 'custom',
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """

    @classmethod
    def init_table(cls, conn: sqlite3.Connection) -> None:
        """Create table and run lightweight migrations."""
        conn.execute(cls.get_create_table_sql())

        # Migrations for older databases.
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(api_keys)").fetchall()}
        if "provider" not in cols:
            conn.execute("ALTER TABLE api_keys ADD COLUMN provider TEXT NOT NULL DEFAULT 'grsai'")
        if "name" not in cols:
            conn.execute("ALTER TABLE api_keys ADD COLUMN name TEXT DEFAULT ''")
        if "base_url" not in cols:
            conn.execute("ALTER TABLE api_keys ADD COLUMN base_url TEXT DEFAULT ''")

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ApiKey":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            provider=row["provider"] if "provider" in row.keys() else "grsai",
            name=row["name"] if "name" in row.keys() else "",
            base_url=row["base_url"] if "base_url" in row.keys() else "",
            value=row["value"],
            source=row["source"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        )

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "name": self.name,
            "base_url": self.base_url,
            "source": self.source,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

    @classmethod
    def get_by_user_id(cls, user_id: int, provider: Optional[str] = None) -> List["ApiKey"]:
        from ..services.database import get_db_manager

        db = get_db_manager()
        if provider:
            rows = db.fetch_all(
                "SELECT * FROM api_keys WHERE user_id = ? AND provider = ? ORDER BY created_at ASC",
                (user_id, provider),
            )
        else:
            rows = db.fetch_all(
                "SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at ASC",
                (user_id,),
            )
        return [cls.from_row(row) for row in rows]

    @classmethod
    def get_active_key(cls, user_id: int, provider: str) -> Optional["ApiKey"]:
        from ..services.database import get_db_manager

        db = get_db_manager()
        row = db.fetch_one(
            "SELECT * FROM api_keys WHERE user_id = ? AND provider = ? AND is_active = 1",
            (user_id, provider),
        )
        return cls.from_row(row) if row else None

    def save(self) -> None:
        from ..services.database import get_db_manager

        db = get_db_manager()

        # Ensure only one active key per provider.
        if self.is_active and self.user_id:
            db.execute_query(
                "UPDATE api_keys SET is_active = 0 WHERE user_id = ? AND provider = ?",
                (self.user_id, self.provider),
            )

        db.execute_query(
            """
            INSERT INTO api_keys (id, user_id, provider, name, base_url, value, source, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                provider = excluded.provider,
                name = excluded.name,
                base_url = excluded.base_url,
                value = excluded.value,
                source = excluded.source,
                is_active = excluded.is_active
            """,
            (
                self.id,
                self.user_id,
                self.provider,
                self.name,
                self.base_url,
                self.value,
                self.source,
                1 if self.is_active else 0,
            ),
        )

    @classmethod
    def delete_by_id(cls, key_id: str, user_id: int) -> bool:
        from ..services.database import get_db_manager

        db = get_db_manager()
        row = db.fetch_one(
            "SELECT id FROM api_keys WHERE id = ? AND user_id = ?",
            (key_id, user_id),
        )
        if not row:
            return False
        db.execute_query("DELETE FROM api_keys WHERE id = ?", (key_id,))
        return True

    @classmethod
    def set_active_key(cls, key_id: str, user_id: int) -> bool:
        """Set active key for this key's provider."""
        from ..services.database import get_db_manager

        db = get_db_manager()
        row = db.fetch_one(
            "SELECT id, provider FROM api_keys WHERE id = ? AND user_id = ?",
            (key_id, user_id),
        )
        if not row:
            return False

        provider = row["provider"] if "provider" in row.keys() else "grsai"
        db.execute_query(
            "UPDATE api_keys SET is_active = 0 WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        )
        db.execute_query("UPDATE api_keys SET is_active = 1 WHERE id = ?", (key_id,))
        return True

    @classmethod
    def get_decrypted_keys(
        cls,
        user_id: int,
        decrypt_func: Callable[[str], str],
    ) -> Tuple[List[Dict], Dict[str, str]]:
        """Return decrypted key list and active key ids by provider."""
        keys = cls.get_by_user_id(user_id)
        decrypted: List[Dict] = []
        active_by_provider: Dict[str, str] = {}

        for key in keys:
            decrypted_value = decrypt_func(key.value)
            if not decrypted_value:
                continue

            decrypted.append(
                {
                    "id": key.id,
                    "provider": key.provider,
                    "name": key.name,
                    "base_url": key.base_url,
                    "value": decrypted_value,
                    "source": key.source,
                    "created_at": key.created_at,
                }
            )
            if key.is_active:
                active_by_provider[key.provider] = key.id

        return decrypted, active_by_provider
