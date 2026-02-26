"""
OCR 数据源模块

包含：
    - AzureOCR: Azure Document Intelligence OCR
    - Pix2TextOCR: Pix2Text 公式识别

这些是数据源层，一般不需要修改。
"""

from .azure import AzureOCR, TextBlock, OCRResult

try:
    from .pix2text import Pix2TextOCR, Pix2TextBlock, Pix2TextResult
    PIX2TEXT_AVAILABLE = True
except Exception:
    # Keep OCR package importable when optional pix2text dependency is missing.
    Pix2TextOCR = None
    Pix2TextBlock = None
    Pix2TextResult = None
    PIX2TEXT_AVAILABLE = False

__all__ = [
    'AzureOCR',
    'TextBlock',
    'OCRResult',
    'Pix2TextOCR',
    'Pix2TextBlock',
    'Pix2TextResult',
    'PIX2TEXT_AVAILABLE',
]
