"""Edit-Banana integration service.

Bridges sibling `Edit-Banana` project into nano_banana.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import traceback
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..config import get_config
from ..utils.errors import ServiceError, ValidationError


@dataclass(frozen=True)
class EditBananaStatus:
    root: Optional[str]
    root_exists: bool
    config_exists: bool
    torch_available: bool
    cuda_available: bool
    cv2_available: bool
    text_module_available: bool

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "rootExists": self.root_exists,
            "configExists": self.config_exists,
            "torchAvailable": self.torch_available,
            "cudaAvailable": self.cuda_available,
            "cv2Available": self.cv2_available,
            "textModuleAvailable": self.text_module_available,
        }


class EditBananaService:
    def __init__(self):
        self.config = get_config()
        self._root: Optional[Path] = None
        self._main: Any = None
        self._pipeline: Any = None

    def _abspath(self, root: Path, value: str) -> str:
        if not value:
            return value
        p = Path(value)
        if p.is_absolute():
            return str(p)
        return str((root / p).resolve())

    def _resolve_root(self) -> Optional[Path]:
        if self._root is not None:
            return self._root

        env_root = (os.getenv("EDIT_BANANA_ROOT") or "").strip()
        if env_root:
            candidate = Path(env_root).expanduser().resolve()
            if candidate.exists() and candidate.is_dir():
                self._root = candidate
                return self._root

        project_root = Path(__file__).resolve().parents[2]
        sibling = (project_root / "integrations" / "Edit-Banana").resolve()
        if sibling.exists() and sibling.is_dir():
            self._root = sibling
            return self._root

        self._root = None
        return None

    def get_status(self) -> EditBananaStatus:
        root = self._resolve_root()
        root_exists = bool(root and root.exists())
        config_exists = bool(root and (root / "config" / "config.yaml").exists())

        torch_available = False
        cuda_available = False
        try:
            import torch  # type: ignore

            torch_available = True
            try:
                cuda_available = bool(torch.cuda.is_available())
            except Exception:
                cuda_available = False
        except Exception:
            torch_available = False
            cuda_available = False

        cv2_available = False
        try:

            cv2_available = True
        except Exception:
            cv2_available = False

        text_module_available = False
        try:
            main = self._load_main()
            text_module_available = bool(getattr(main, "TEXT_MODULE_AVAILABLE", False))
        except Exception:
            text_module_available = False

        return EditBananaStatus(
            root=str(root) if root else None,
            root_exists=root_exists,
            config_exists=config_exists,
            torch_available=torch_available,
            cuda_available=cuda_available,
            cv2_available=cv2_available,
            text_module_available=text_module_available,
        )

    def _load_main(self) -> Any:
        if self._main is not None:
            return self._main

        root = self._resolve_root()
        if not root:
            raise ServiceError(
                "Edit-Banana not found. Set EDIT_BANANA_ROOT or place Edit-Banana next to nano_banana."
            )

        main_py = root / "main.py"
        if not main_py.exists():
            raise ServiceError(f"Edit-Banana entry not found: {main_py}")

        spec = importlib.util.spec_from_file_location("edit_banana_main", str(main_py))
        if spec is None or spec.loader is None:
            raise ServiceError("Failed to import Edit-Banana main.py")

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
        except Exception as exc:
            raise ServiceError("Failed to load Edit-Banana.", details=str(exc))

        self._main = module
        return self._main

    def _get_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        main = self._load_main()
        root = self._resolve_root()
        if not root:
            raise ServiceError("Edit-Banana root not configured")

        try:
            cfg = main.load_config()

            sam3_cfg = cfg.get("sam3", {}) if isinstance(cfg, dict) else {}
            ckpt = sam3_cfg.get("checkpoint_path")
            bpe = sam3_cfg.get("bpe_path")
            if isinstance(ckpt, str):
                sam3_cfg["checkpoint_path"] = self._abspath(root, ckpt)
            if isinstance(bpe, str):
                sam3_cfg["bpe_path"] = self._abspath(root, bpe)
            if isinstance(cfg, dict):
                cfg["sam3"] = sam3_cfg

            self._pipeline = main.Pipeline(cfg)
            return self._pipeline
        except Exception as exc:
            raise ServiceError("Failed to initialize Edit-Banana pipeline.", details=str(exc))

    def convert_to_drawio(
        self, input_path: Path, *, with_text: bool = True, with_refinement: bool = False
    ) -> Path:
        if not input_path.exists():
            raise ValidationError("Input file not found")

        root = self._resolve_root()
        if not root:
            raise ServiceError("Edit-Banana root not configured")

        cfg_path = root / "config" / "config.yaml"
        if not cfg_path.exists():
            raise ServiceError(f"Edit-Banana missing config: {cfg_path}")

        main = self._load_main()
        text_module_available = bool(getattr(main, "TEXT_MODULE_AVAILABLE", False))
        effective_with_text = bool(with_text and text_module_available)
        pipeline = self._get_pipeline()

        jobs_root = Path(self.config.data_dir) / "edit_banana" / "jobs"
        jobs_root.mkdir(parents=True, exist_ok=True)
        job_dir = jobs_root / uuid.uuid4().hex
        job_dir.mkdir(parents=True, exist_ok=True)

        job_input = job_dir / f"input{input_path.suffix.lower()}"
        shutil.copyfile(str(input_path), str(job_input))

        try:
            result_path = pipeline.process_image(
                str(job_input),
                output_dir=str(job_dir),
                with_refinement=with_refinement,
                with_text=effective_with_text,
            )
        except Exception as exc:
            # OCR 依赖缺失时，做一次强制降级重试，避免因 with_text=True 直接失败。
            err_text = f"{type(exc).__name__}: {exc}"
            ocr_missing = ("pix2text" in err_text.lower()) or ("textrestorer" in err_text.lower())
            if effective_with_text and ocr_missing:
                try:
                    result_path = pipeline.process_image(
                        str(job_input),
                        output_dir=str(job_dir),
                        with_refinement=with_refinement,
                        with_text=False,
                    )
                except Exception as retry_exc:
                    raise ServiceError(
                        "Edit-Banana conversion failed.",
                        details=f"{type(retry_exc).__name__}: {retry_exc}\n{traceback.format_exc()}",
                    )
            else:
                raise ServiceError(
                    "Edit-Banana conversion failed.",
                    details=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                )

        if not result_path:
            raise ServiceError("Edit-Banana conversion returned empty result")

        out = Path(result_path)
        if not out.exists():
            raise ServiceError(f"Edit-Banana output not found: {out}")
        return out


_service: Optional[EditBananaService] = None


def get_edit_banana_service() -> EditBananaService:
    global _service
    if _service is None:
        _service = EditBananaService()
    return _service
