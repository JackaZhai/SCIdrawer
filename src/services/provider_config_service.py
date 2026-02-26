"""Provider config service.

Stores per-user per-provider default text/image models.
"""

from __future__ import annotations

from typing import Dict, Optional

from ..models.provider_config import ProviderConfig
from ..utils.errors import ValidationError
from .api_key_service import get_api_key_service

DEFAULT_MODELS: Dict[str, Dict[str, str]] = {
    # grsai defaults: language/image split
    "grsai": {"textModel": "gemini-2.5-pro", "imageModel": "nano-banana-pro"},
    "openai": {"textModel": "gpt-4o-mini", "imageModel": "gpt-image-1"},
    "deepseek": {"textModel": "deepseek-chat", "imageModel": "gpt-image-1"},
    "openrouter": {"textModel": "openai/gpt-4o-mini", "imageModel": "gpt-image-1"},
    # Anthropic text-only; image will still require OpenAI-compatible provider unless user selects otherwise
    "anthropic": {"textModel": "claude-3-5-sonnet-latest", "imageModel": "gpt-image-1"},
    "google": {"textModel": "gemini-2.5-pro", "imageModel": "gemini-3-pro-image-preview"},
}


class ProviderConfigService:
    def __init__(self):
        self.api_key_service = get_api_key_service()

    def normalize_provider(self, provider: str) -> str:
        return self.api_key_service.normalize_provider(provider)

    def get_defaults(self, user_id: int, provider: str) -> Dict[str, str]:
        provider = self.normalize_provider(provider)
        row = ProviderConfig.get_by_user_provider(user_id, provider)
        if row:
            return {
                "provider": provider,
                "textModel": row.text_model
                or DEFAULT_MODELS.get(provider, {}).get("textModel", ""),
                "imageModel": row.image_model
                or DEFAULT_MODELS.get(provider, {}).get("imageModel", ""),
            }
        return {
            "provider": provider,
            "textModel": DEFAULT_MODELS.get(provider, {}).get("textModel", ""),
            "imageModel": DEFAULT_MODELS.get(provider, {}).get("imageModel", ""),
        }

    def list_all(self, user_id: int) -> Dict[str, Dict[str, str]]:
        # We don't have a list query; use known providers + active key providers.
        from ..models.api_key import ApiKey

        providers = set(DEFAULT_MODELS.keys())
        for key in ApiKey.get_by_user_id(user_id):
            providers.add((key.provider or "").strip().lower())

        result: Dict[str, Dict[str, str]] = {}
        for p in sorted(providers):
            if not p:
                continue
            result[p] = self.get_defaults(user_id, p)
        return result

    def upsert(
        self, user_id: int, provider: str, text_model: str, image_model: str
    ) -> Dict[str, str]:
        provider = self.normalize_provider(provider)
        text_model = (text_model or "").strip()
        image_model = (image_model or "").strip()
        if not provider:
            raise ValidationError("provider 不能为空")
        if not text_model and not image_model:
            raise ValidationError("textModel/imageModel 至少填写一个")

        current = ProviderConfig.get_by_user_provider(user_id, provider)
        if current:
            current.text_model = text_model or current.text_model
            current.image_model = image_model or current.image_model
            current.save()
        else:
            ProviderConfig(
                user_id=user_id,
                provider=provider,
                text_model=text_model,
                image_model=image_model,
            ).save()

        return self.get_defaults(user_id, provider)


_provider_config_service: Optional[ProviderConfigService] = None


def get_provider_config_service() -> ProviderConfigService:
    global _provider_config_service
    if _provider_config_service is None:
        _provider_config_service = ProviderConfigService()
    return _provider_config_service
