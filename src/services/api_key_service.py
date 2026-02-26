"""API key service.

Keys are encrypted at rest and stored per-user.
Supports multiple providers and one active key per provider.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Tuple

from ..config import get_config
from ..models.api_key import ApiKey
from ..utils.encryption import get_encryption_service
from ..utils.errors import NotFoundError, ValidationError

OPENAI_COMPAT_DEFAULTS: Dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


class ApiKeyService:
    def __init__(self):
        self.config = get_config()
        self.encryption = get_encryption_service()

    def bootstrap_api_keys(self, user_id: Optional[int]) -> None:
        """Normalize stored keys only; do not import env/config keys."""
        if not user_id:
            return

        keys, active_by_provider = self.get_decrypted_keys(user_id)
        changed = False

        # Remove legacy env-imported keys; keep only user-saved keys.
        filtered_keys = [k for k in keys if (k.get("source") or "custom") != "env"]
        if len(filtered_keys) != len(keys):
            keys = filtered_keys
            changed = True

        # Ensure each provider keeps one active key if possible.
        providers = {k.get("provider") for k in keys if k.get("provider")}
        for provider in list(active_by_provider.keys()):
            active_id = active_by_provider.get(provider)
            if provider not in providers or not any(k.get("id") == active_id for k in keys):
                first = next((k for k in keys if k.get("provider") == provider), None)
                if first:
                    active_by_provider[provider] = first["id"]
                else:
                    active_by_provider.pop(provider, None)
                changed = True

        if changed:
            self.save_key_store(keys, active_by_provider, user_id)

    def _default_base_url(self, provider: str) -> str:
        provider = (provider or "").strip().lower()
        if provider == "grsai":
            return f"{self.config.api_host.rstrip('/')}/v1"
        if provider in OPENAI_COMPAT_DEFAULTS:
            return OPENAI_COMPAT_DEFAULTS[provider]
        if provider == "anthropic":
            return "https://api.anthropic.com"
        return ""

    def normalize_provider(self, provider: str) -> str:
        p = (provider or "").strip().lower()
        # aliases
        if p in {"chatgpt", "gpt", "openai"}:
            return "openai"
        if p in {"claude", "anthropic"}:
            return "anthropic"
        if p in {"openrouter", "openruter"}:
            return "openrouter"
        if p in {"grsai", "grs"}:
            return "grsai"
        if p in {"deepseek"}:
            return "deepseek"
        if p in {"google", "gemini"}:
            return "google"
        return p or "grsai"

    def get_decrypted_keys(self, user_id: int) -> Tuple[List[Dict], Dict[str, str]]:
        return ApiKey.get_decrypted_keys(user_id, self.encryption.decrypt)

    def save_key_store(
        self, keys: List[Dict], active_by_provider: Dict[str, str], user_id: int
    ) -> None:
        from ..services.database import get_db_manager

        db = get_db_manager()
        db.execute_query("DELETE FROM api_keys WHERE user_id = ?", (user_id,))

        for item in keys:
            provider = self.normalize_provider(item.get("provider") or "grsai")
            key = ApiKey(
                id=item.get("id"),
                user_id=user_id,
                provider=provider,
                name=item.get("name") or "",
                base_url=item.get("base_url") or "",
                value=self.encryption.encrypt(item.get("value", "")),
                source=item.get("source", "custom"),
                is_active=(item.get("id") == active_by_provider.get(provider)),
            )
            key.save()

    def get_active_api_key_value(self, user_id: Optional[int], provider: str = "grsai") -> str:
        provider = self.normalize_provider(provider)
        if not user_id:
            return ""

        keys, active_by_provider = self.get_decrypted_keys(user_id)
        active_id = active_by_provider.get(provider)
        if active_id:
            for item in keys:
                if item.get("id") == active_id:
                    return item.get("value", "")

        return ""

    def get_active_base_url(self, user_id: Optional[int], provider: str = "grsai") -> str:
        provider = self.normalize_provider(provider)
        if not user_id:
            return self._default_base_url(provider)

        keys, active_by_provider = self.get_decrypted_keys(user_id)
        active_id = active_by_provider.get(provider)
        if active_id:
            for item in keys:
                if item.get("id") == active_id:
                    v = (item.get("base_url") or "").strip()
                    return v or self._default_base_url(provider)
        return self._default_base_url(provider)

    def serialize_keys(self, user_id: int) -> Dict:
        keys, active_by_provider = self.get_decrypted_keys(user_id)
        return {
            "activeByProvider": active_by_provider,
            "providers": sorted(list({k.get("provider") for k in keys if k.get("provider")})),
            "keys": [
                {
                    "id": item.get("id"),
                    "provider": item.get("provider"),
                    "name": item.get("name") or "",
                    "baseUrl": item.get("base_url") or "",
                    "mask": self.encryption.mask_key(item.get("value", "")),
                    "source": item.get("source", "custom"),
                    "isActive": item.get("id") == active_by_provider.get(item.get("provider")),
                    "createdAt": item.get("created_at"),
                }
                for item in keys
            ],
        }

    def add_api_key(
        self, user_id: int, provider: str, value: str, name: str = "", base_url: str = ""
    ) -> Dict:
        provider = self.normalize_provider(provider)
        value = (value or "").strip()
        if not value:
            raise ValidationError("Api key 不能为空")

        keys, active_by_provider = self.get_decrypted_keys(user_id)
        if any(k.get("provider") == provider and k.get("value") == value for k in keys):
            raise ValidationError("Api key 已存在")

        base_url = (base_url or "").strip()
        if not base_url:
            base_url = self._default_base_url(provider)

        new_item = {
            "id": uuid.uuid4().hex,
            "provider": provider,
            "name": (name or "").strip(),
            "base_url": base_url,
            "value": value,
            "source": "custom",
        }
        keys.append(new_item)
        active_by_provider[provider] = new_item["id"]

        self.save_key_store(keys, active_by_provider, user_id)
        return self.serialize_keys(user_id)

    def delete_api_key(self, user_id: int, key_id: str) -> Dict:
        if not ApiKey.delete_by_id(key_id, user_id):
            raise NotFoundError("未找到对应的 Api key")

        # Ensure each provider keeps an active key if possible.
        keys, active_by_provider = self.get_decrypted_keys(user_id)
        for provider in list(active_by_provider.keys()):
            if active_by_provider.get(provider) and not any(
                k.get("id") == active_by_provider[provider] for k in keys
            ):
                # pick first remaining key for provider
                first = next((k for k in keys if k.get("provider") == provider), None)
                if first:
                    active_by_provider[provider] = first["id"]
                else:
                    active_by_provider.pop(provider, None)

        self.save_key_store(keys, active_by_provider, user_id)
        return self.serialize_keys(user_id)

    def set_active_key(self, user_id: int, key_id: str) -> Dict:
        if not ApiKey.set_active_key(key_id, user_id):
            raise ValidationError("无效的 Api key")
        return self.serialize_keys(user_id)

    def build_headers(self, user_id: Optional[int], provider: str = "grsai") -> Dict[str, str]:
        provider = self.normalize_provider(provider)
        api_key = self.get_active_api_key_value(user_id, provider)
        if not api_key:
            raise ValidationError("Missing API key. 请在“API 密钥”中添加对应提供商的 Key。")

        if provider == "anthropic":
            return {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }

        # Default: OpenAI-compatible
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }


_api_key_service: Optional[ApiKeyService] = None


def get_api_key_service() -> ApiKeyService:
    global _api_key_service
    if _api_key_service is None:
        _api_key_service = ApiKeyService()
    return _api_key_service
