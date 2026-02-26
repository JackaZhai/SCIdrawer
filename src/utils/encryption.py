"""
加密工具
"""

import base64
from hashlib import sha256
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


class EncryptionService:
    """加密服务"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self._cipher = None

    @property
    def cipher(self) -> Fernet:
        """获取加密器（懒加载）"""
        if self._cipher is None:
            secret = str(self.secret_key or "change-me")
            digest = sha256(secret.encode("utf-8")).digest()
            key = base64.urlsafe_b64encode(digest)
            self._cipher = Fernet(key)
        return self._cipher

    def encrypt(self, value: str) -> str:
        """加密值"""
        if not value:
            return ""
        return self.cipher.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, token: str) -> str:
        """解密值"""
        if not token:
            return ""
        try:
            return self.cipher.decrypt(token.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            return ""

    @staticmethod
    def mask_key(value: str) -> str:
        """掩码显示API密钥"""
        if not value:
            return ""
        if len(value) <= 8:
            return f"***{value[-2:]}"
        return f"{value[:4]}...{value[-4:]}"


# 全局加密服务实例
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """获取加密服务实例（单例模式）"""
    global _encryption_service
    if _encryption_service is None:
        from ..config import get_config

        config = get_config()
        _encryption_service = EncryptionService(config.app_secret_key)
    return _encryption_service
