"""Local OCR adapter based on cnocr.

This adapter mirrors the Azure OCR return shape so downstream processors
can remain unchanged.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, List, Tuple

from PIL import Image

from .azure import OCRResult, TextBlock


class LocalCnOcr:
    """Local OCR backend using cnocr."""

    def __init__(self):
        from cnocr import CnOcr

        self._ocr = CnOcr()

    def analyze_image(self, image_path: str) -> OCRResult:
        image = Path(image_path)
        if not image.exists():
            raise FileNotFoundError(f"Image not found: {image}")

        with Image.open(image) as img:
            width, height = img.size

        raw = self._ocr.ocr(str(image))
        blocks: List[TextBlock] = []
        for item in raw:
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            polygon = self._to_polygon(item.get("position"))
            blocks.append(
                TextBlock(
                    text=text,
                    polygon=polygon,
                    confidence=float(item.get("score") or 1.0),
                    font_size_px=self._estimate_font_size(polygon),
                )
            )

        return OCRResult(
            image_width=width,
            image_height=height,
            text_blocks=blocks,
            styles=[],
        )

    def _to_polygon(self, pos: object) -> List[Tuple[float, float]]:
        if pos is None:
            return [(0.0, 0.0)] * 4

        if hasattr(pos, "tolist"):
            pos = pos.tolist()

        points: List[Tuple[float, float]] = []
        if isinstance(pos, Iterable):
            for p in pos:
                if isinstance(p, Iterable):
                    p = list(p)
                    if len(p) >= 2:
                        points.append((float(p[0]), float(p[1])))

        while len(points) < 4:
            points.append((0.0, 0.0))
        return points[:4]

    def _estimate_font_size(self, polygon: List[Tuple[float, float]]) -> float:
        if len(polygon) < 4:
            return 12.0
        p0, p1, _, p3 = polygon[:4]
        edge1 = math.sqrt((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2)
        edge2 = math.sqrt((p3[0] - p0[0]) ** 2 + (p3[1] - p0[1]) ** 2)
        value = min(edge1, edge2)
        return value if value > 0 else 12.0
