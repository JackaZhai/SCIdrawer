"""
验证工具
"""

from typing import List, Optional

from .errors import ValidationError


class ValidationService:
    """验证服务"""

    def __init__(self, max_reference_images: int, max_reference_image_bytes: int):
        self.max_reference_images = max_reference_images
        self.max_reference_image_bytes = max_reference_image_bytes

    def sanitize_urls(self, urls: Optional[List[str]]) -> List[str]:
        """清理URL列表"""
        if not urls:
            return []
        cleaned = []
        for raw in urls:
            if not raw:
                continue
            value = raw.strip()
            if value:
                cleaned.append(value)
        return cleaned

    def validate_reference_images(self, urls: List[str]) -> None:
        """验证参考图片"""
        if len(urls) > self.max_reference_images:
            raise ValidationError(f"参考图数量最多 {self.max_reference_images} 张")

        for url in urls:
            if url.startswith("data:"):
                try:
                    header, encoded = url.split(",", 1)
                except ValueError:
                    raise ValidationError("参考图数据格式无效")

                approx_size = len(encoded) * 3 // 4
                if approx_size > self.max_reference_image_bytes:
                    max_mb = self.max_reference_image_bytes // (1024 * 1024)
                    raise ValidationError(f"单张参考图大小超出限制（最大 {max_mb} MB）")

    def validate_prompt(self, prompt: str) -> None:
        """验证提示词"""
        if not prompt or not prompt.strip():
            raise ValidationError("Prompt is required")

    def validate_draw_id(self, draw_id: str) -> None:
        """验证绘图ID"""
        if not draw_id or not draw_id.strip():
            raise ValidationError("id is required")

    def validate_api_key(self, api_key: str) -> None:
        """验证API密钥"""
        if not api_key or not api_key.strip():
            raise ValidationError("Api key 不能为空")

    def validate_messages(self, messages: List) -> None:
        """验证消息列表"""
        if not messages:
            raise ValidationError("messages is required")


# 全局验证服务实例
_validation_service: Optional[ValidationService] = None


def get_validation_service() -> ValidationService:
    """获取验证服务实例（单例模式）"""
    global _validation_service
    if _validation_service is None:
        from ..config import get_config

        config = get_config()
        _validation_service = ValidationService(
            max_reference_images=config.max_reference_images,
            max_reference_image_bytes=config.max_reference_image_bytes,
        )
    return _validation_service
