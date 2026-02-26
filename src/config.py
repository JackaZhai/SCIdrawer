"""Configuration management."""

from __future__ import annotations

import os
from typing import Optional


class Config:
    """App configuration container."""

    def __init__(self) -> None:
        try:
            import config as local_config  # type: ignore

            self.local_config = local_config
        except ImportError:
            self.local_config = None

        self.app_secret_key = os.getenv("APP_SECRET_KEY", "change-me")

        # Provider host defaults to latest grsai overseas endpoint.
        self.api_host = self._get_config_value(
            "API_HOST", "NANO_BANANA_HOST", "https://grsaiapi.com"
        )
        self.api_key = self._get_config_value("API_KEY", "NANO_BANANA_API_KEY", "")

        self.seed_username = self._get_config_value("AUTH_USERNAME", "APP_USERNAME", "admin")
        self.seed_password = self._get_config_value("AUTH_PASSWORD", "APP_PASSWORD", "banana123")

        self.port = int(os.getenv("PORT", "5001"))

        self.data_dir = os.getenv("DATA_DIR", "data")
        self.db_path = os.getenv("DB_PATH", os.path.join(self.data_dir, "app.db"))

        self.max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.lock_minutes = int(os.getenv("LOCK_MINUTES", "10"))
        self.max_reference_images = int(os.getenv("MAX_REFERENCE_IMAGES", "3"))
        self.max_reference_image_bytes = int(
            os.getenv("MAX_REFERENCE_IMAGE_BYTES", str(5 * 1024 * 1024))
        )

    def _get_config_value(self, config_attr: str, env_var: str, default: str) -> str:
        env_value = os.getenv(env_var)
        if env_value is not None:
            return env_value

        if self.local_config:
            config_value = getattr(self.local_config, config_attr, None)
            if config_value is not None:
                return config_value

        return default

    @property
    def draw_endpoint(self) -> str:
        return f"{self.api_host.rstrip('/')}/v1/draw/completions"

    @property
    def result_endpoint(self) -> str:
        return f"{self.api_host.rstrip('/')}/v1/draw/result"

    @property
    def chat_endpoint(self) -> str:
        return f"{self.api_host.rstrip('/')}/v1/chat/completions"

    def to_dict(self) -> dict:
        return {
            "api_host": self.api_host,
            "draw_endpoint": self.draw_endpoint,
            "result_endpoint": self.result_endpoint,
            "chat_endpoint": self.chat_endpoint,
            "seed_username": self.seed_username,
            "port": self.port,
            "db_path": self.db_path,
            "max_login_attempts": self.max_login_attempts,
            "lock_minutes": self.lock_minutes,
            "max_reference_images": self.max_reference_images,
            "max_reference_image_bytes": self.max_reference_image_bytes,
        }


_config_instance: Optional[Config] = None


def get_config() -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
