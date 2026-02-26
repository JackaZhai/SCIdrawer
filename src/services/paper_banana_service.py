"""PaperBanana integration service.

Runs the local PaperBanana (PaperVizAgent) pipeline as a background job and
exposes results via nano_banana APIs.

This service wires provider keys from nano_banana's API key store into
PaperBanana via environment variables.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import get_config
from ..utils.errors import NotFoundError, ServiceError, ValidationError
from .api_key_service import get_api_key_service


@dataclass(frozen=True)
class PaperBananaJob:
    job_id: str
    status: str  # running | succeeded | failed
    progress: int
    stage: str = "queued"
    stage_message: Optional[str] = None
    output_image_path: Optional[str] = None
    error: Optional[str] = None


class PaperBananaService:
    def __init__(self):
        self.config = get_config()
        self.root = Path(__file__).resolve().parents[2] / "integrations" / "PaperBanana"
        self.jobs_root = Path(self.config.data_dir) / "paperbanana" / "jobs"
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.api_key_service = get_api_key_service()

    def _job_dir(self, job_id: str) -> Path:
        return self.jobs_root / job_id

    def _status_file(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "status.json"

    def _cancel_file(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "cancelled.flag"

    def _write_status(self, job: PaperBananaJob) -> None:
        self._job_dir(job.job_id).mkdir(parents=True, exist_ok=True)
        payload = {
            "jobId": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "stage": job.stage,
            "stageMessage": job.stage_message,
            "outputImagePath": job.output_image_path,
            "error": job.error,
        }
        self._status_file(job.job_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_status(self, job_id: str) -> PaperBananaJob:
        p = self._status_file(job_id)
        if not p.exists():
            raise NotFoundError("Job not found")
        data = json.loads(p.read_text(encoding="utf-8"))
        return PaperBananaJob(
            job_id=data.get("jobId") or job_id,
            status=data.get("status") or "failed",
            progress=int(data.get("progress") or 0),
            stage=(data.get("stage") or "queued"),
            stage_message=data.get("stageMessage"),
            output_image_path=data.get("outputImagePath"),
            error=data.get("error"),
        )

    def _is_cancelled(self, job_id: str) -> bool:
        return self._cancel_file(job_id).exists()

    def _ensure_not_cancelled(self, job_id: str) -> None:
        if self._is_cancelled(job_id):
            raise ServiceError("任务已取消")

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        job = self._read_status(job_id)
        if job.status in {"succeeded", "failed"}:
            return {"id": job_id, "status": job.status, "cancelled": False}

        cancel_file = self._cancel_file(job_id)
        cancel_file.parent.mkdir(parents=True, exist_ok=True)
        cancel_file.write_text("1", encoding="utf-8")

        self._write_status(
            PaperBananaJob(
                job_id=job_id,
                status="failed",
                progress=100,
                stage="failed",
                error="任务已取消",
            )
        )
        return {"id": job_id, "status": "failed", "cancelled": True}

    def submit_diagram(
        self,
        *,
        user_id: Optional[int],
        provider: str,
        text_provider: Optional[str] = None,
        image_provider: Optional[str] = None,
        text_model: str,
        image_model: str,
        method_content: str,
        caption: str,
        aspect_ratio: str = "16:9",
        image_size: str = "1K",
        pipeline_mode: str = "full",
        max_critic_rounds: Optional[int] = None,
        exp_mode: str = "",
        retrieval_setting: str = "",
        critic_enabled: Optional[bool] = None,
        eval_enabled: Optional[bool] = None,
    ) -> str:
        method_content = (method_content or "").strip()
        caption = (caption or "").strip()
        if not method_content and not caption:
            raise ValidationError("prompt/caption 不能为空")

        provider = self.api_key_service.normalize_provider(provider or "grsai")
        text_model = (text_model or "").strip()
        image_model = (image_model or "").strip()
        if not text_model or not image_model:
            raise ValidationError("text_model/image_model 不能为空")

        job_id = uuid.uuid4().hex
        self._write_status(
            PaperBananaJob(
                job_id=job_id,
                status="running",
                progress=1,
                stage="queued",
            )
        )

        thread = threading.Thread(
            target=self._run_job_safe,
            args=(
                job_id,
                user_id,
                provider,
                text_provider,
                image_provider,
                text_model,
                image_model,
                method_content,
                caption,
                aspect_ratio,
                image_size,
                pipeline_mode,
                max_critic_rounds,
                exp_mode,
                retrieval_setting,
                critic_enabled,
                eval_enabled,
            ),
            daemon=True,
        )
        thread.start()
        return job_id

    def _run_job_safe(
        self,
        job_id: str,
        user_id: Optional[int],
        provider: str,
        text_provider: Optional[str],
        image_provider: Optional[str],
        text_model: str,
        image_model: str,
        method_content: str,
        caption: str,
        aspect_ratio: str,
        image_size: str,
        pipeline_mode: str,
        max_critic_rounds: Optional[int],
        exp_mode: str,
        retrieval_setting: str,
        critic_enabled: Optional[bool],
        eval_enabled: Optional[bool],
    ) -> None:
        try:
            self._run_job(
                job_id,
                user_id,
                provider,
                text_provider,
                image_provider,
                text_model,
                image_model,
                method_content,
                caption,
                aspect_ratio,
                image_size,
                pipeline_mode,
                max_critic_rounds,
                exp_mode,
                retrieval_setting,
                critic_enabled,
                eval_enabled,
            )
        except Exception as exc:
            self._write_status(
                PaperBananaJob(
                    job_id=job_id,
                    status="failed",
                    progress=100,
                    stage="failed",
                    error=str(exc),
                )
            )

    def _apply_provider_env(
        self,
        user_id: Optional[int],
        provider: str,
        text_provider: Optional[str],
        image_provider: Optional[str],
        text_model: str,
        image_model: str,
    ) -> None:
        provider = self.api_key_service.normalize_provider(provider)
        text_provider = self.api_key_service.normalize_provider(text_provider or provider)
        image_provider = self.api_key_service.normalize_provider(image_provider or provider)

        def _normalize_openai_base(p: str, base_url: str) -> str:
            b = (base_url or "").strip().rstrip("/")
            if p == "grsai":
                # Avoid legacy host causing SSL EOF on this environment.
                if (not b) or ("api.grsai.com" in b.lower()):
                    b = "https://grsai.dakka.com.cn/v1"
                elif not b.lower().endswith("/v1"):
                    b = f"{b}/v1"
            return b

        def _is_openai_compat(p: str) -> bool:
            return p not in {"google", "anthropic"}

        # Explicit provider binding only; do not infer provider from model name.
        text_needs_google = text_provider == "google"
        image_needs_google = image_provider == "google"
        needs_google = text_needs_google or image_needs_google

        text_needs_anthropic = text_provider == "anthropic"
        image_needs_anthropic = image_provider == "anthropic"
        needs_anthropic = text_needs_anthropic or image_needs_anthropic

        text_needs_openai = (
            not text_needs_google and not text_needs_anthropic
        ) and _is_openai_compat(text_provider)
        image_needs_openai = (
            not image_needs_google and not image_needs_anthropic
        ) and _is_openai_compat(image_provider)
        needs_openai = text_needs_openai or image_needs_openai

        if needs_google:
            key = self.api_key_service.get_active_api_key_value(user_id, provider="google")
            if not key:
                raise ServiceError("Missing GOOGLE API key (provider=google)")
            os.environ["GOOGLE_API_KEY"] = key

        if needs_anthropic:
            key = self.api_key_service.get_active_api_key_value(user_id, provider="anthropic")
            if not key:
                raise ServiceError("Missing Anthropic API key (provider=anthropic)")
            os.environ["ANTHROPIC_API_KEY"] = key

        text_key = None
        text_base_url = ""
        if text_needs_openai:
            text_key = self.api_key_service.get_active_api_key_value(
                user_id, provider=text_provider
            )
            if not text_key:
                raise ServiceError(f"Missing API key for provider={text_provider} (text lane)")
            text_base_url = self.api_key_service.get_active_base_url(
                user_id, provider=text_provider
            )
            text_base_url = _normalize_openai_base(text_provider, text_base_url)

        image_key = None
        image_base_url = ""
        if image_needs_openai:
            image_key = self.api_key_service.get_active_api_key_value(
                user_id, provider=image_provider
            )
            if not image_key:
                raise ServiceError(f"Missing API key for provider={image_provider} (image lane)")
            image_base_url = self.api_key_service.get_active_base_url(
                user_id, provider=image_provider
            )
            image_base_url = _normalize_openai_base(image_provider, image_base_url)

        # Lane-specific OpenAI-compatible credentials.
        if text_key:
            os.environ["OPENAI_TEXT_API_KEY"] = text_key
            if text_base_url:
                os.environ["OPENAI_TEXT_BASE_URL"] = text_base_url
            else:
                os.environ.pop("OPENAI_TEXT_BASE_URL", None)
            os.environ["OPENAI_TEXT_PROVIDER"] = text_provider
        else:
            os.environ.pop("OPENAI_TEXT_API_KEY", None)
            os.environ.pop("OPENAI_TEXT_BASE_URL", None)
            os.environ.pop("OPENAI_TEXT_PROVIDER", None)

        if image_key:
            os.environ["OPENAI_IMAGE_API_KEY"] = image_key
            if image_base_url:
                os.environ["OPENAI_IMAGE_BASE_URL"] = image_base_url
            else:
                os.environ.pop("OPENAI_IMAGE_BASE_URL", None)
            os.environ["OPENAI_IMAGE_PROVIDER"] = image_provider
        else:
            os.environ.pop("OPENAI_IMAGE_API_KEY", None)
            os.environ.pop("OPENAI_IMAGE_BASE_URL", None)
            os.environ.pop("OPENAI_IMAGE_PROVIDER", None)

        # Backward-compatible fallback for callers still reading OPENAI_* only.
        if needs_openai:
            fallback_key = text_key or image_key
            fallback_base_url = text_base_url or image_base_url
            if fallback_key:
                os.environ["OPENAI_API_KEY"] = fallback_key
                if fallback_base_url:
                    os.environ["OPENAI_BASE_URL"] = fallback_base_url
                else:
                    os.environ.pop("OPENAI_BASE_URL", None)
        else:
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("OPENAI_BASE_URL", None)

    def _run_job(
        self,
        job_id: str,
        user_id: Optional[int],
        provider: str,
        text_provider: Optional[str],
        image_provider: Optional[str],
        text_model: str,
        image_model: str,
        method_content: str,
        caption: str,
        aspect_ratio: str,
        image_size: str,
        pipeline_mode: str,
        max_critic_rounds: Optional[int],
        exp_mode: str,
        retrieval_setting: str,
        critic_enabled: Optional[bool],
        eval_enabled: Optional[bool],
    ) -> None:
        if not self.root.exists():
            raise ServiceError(f"PaperBanana not found at {self.root}")

        model_cfg = self.root / "configs" / "model_config.yaml"
        if not model_cfg.exists():
            raise ServiceError(f"Missing PaperBanana config: {model_cfg}")

        self._write_status(
            PaperBananaJob(
                job_id=job_id,
                status="running",
                progress=10,
                stage="initializing",
            )
        )
        self._ensure_not_cancelled(job_id)
        self._apply_provider_env(
            user_id,
            provider,
            text_provider,
            image_provider,
            text_model,
            image_model,
        )

        # Import PaperBanana from its own root.
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))

        self._write_status(
            PaperBananaJob(
                job_id=job_id,
                status="running",
                progress=25,
                stage="loading_agents",
            )
        )
        self._ensure_not_cancelled(job_id)
        # Lazy imports (heavy)
        from agents.critic_agent import CriticAgent
        from agents.planner_agent import PlannerAgent
        from agents.polish_agent import PolishAgent
        from agents.retriever_agent import RetrieverAgent
        from agents.stylist_agent import StylistAgent
        from agents.vanilla_agent import VanillaAgent
        from agents.visualizer_agent import VisualizerAgent
        from utils.paperviz_processor import PaperVizProcessor

        from utils import config as pb_config

        mode = (pipeline_mode or "full").strip().lower()
        requested_exp_mode = (exp_mode or "").strip()
        allowed_exp_modes = {
            "vanilla",
            "dev_planner",
            "dev_planner_stylist",
            "dev_planner_critic",
            "demo_planner_critic",
            "dev_full",
            "demo_full",
            "dev_polish",
            "dev_retriever",
        }

        if requested_exp_mode:
            selected_exp_mode = requested_exp_mode
        elif mode == "image_only":
            selected_exp_mode = "vanilla"
        else:
            # Full PaperBanana pipeline by default:
            # retriever -> planner -> stylist -> visualizer -> critic -> eval
            selected_exp_mode = os.getenv("PAPERBANANA_EXP_MODE", "dev_full")
        if selected_exp_mode not in allowed_exp_modes:
            raise ValidationError(f"Unsupported PaperBanana exp_mode: {selected_exp_mode}")

        selected_retrieval = (retrieval_setting or "").strip() or os.getenv(
            "PAPERBANANA_RETRIEVAL", "none"
        )

        eval_default = os.getenv("PAPERBANANA_DO_EVAL", "1").strip().lower() not in {
            "0",
            "false",
            "no",
        }
        do_eval = eval_default if eval_enabled is None else bool(eval_enabled)
        if selected_exp_mode in {"demo_full", "demo_planner_critic", "dev_retriever"}:
            do_eval = False

        critic_default_rounds = 3
        if max_critic_rounds is None:
            effective_max_critic_rounds = critic_default_rounds
        else:
            effective_max_critic_rounds = max(0, int(max_critic_rounds))
        if critic_enabled is False:
            effective_max_critic_rounds = 0
        if selected_exp_mode not in {
            "dev_full",
            "demo_full",
            "dev_planner_critic",
            "demo_planner_critic",
        }:
            effective_max_critic_rounds = 0

        exp_config = pb_config.ExpConfig(
            dataset_name="PaperBananaBench",
            task_name="diagram",
            split_name="demo",
            exp_mode=selected_exp_mode,
            retrieval_setting=selected_retrieval,
            max_critic_rounds=effective_max_critic_rounds,
            model_name=text_model,
            image_model_name=image_model,
            work_dir=self.root,
        )

        def _update_processing_stage(stage: str, stage_message: str, progress: int) -> None:
            self._write_status(
                PaperBananaJob(
                    job_id=job_id,
                    status="running",
                    progress=max(45, min(84, int(progress))),
                    stage=stage,
                    stage_message=stage_message,
                )
            )
            self._ensure_not_cancelled(job_id)

        processor = PaperVizProcessor(
            exp_config=exp_config,
            vanilla_agent=VanillaAgent(exp_config=exp_config),
            planner_agent=PlannerAgent(exp_config=exp_config),
            visualizer_agent=VisualizerAgent(exp_config=exp_config),
            stylist_agent=StylistAgent(exp_config=exp_config),
            critic_agent=CriticAgent(exp_config=exp_config),
            retriever_agent=RetrieverAgent(exp_config=exp_config),
            polish_agent=PolishAgent(exp_config=exp_config),
            progress_callback=_update_processing_stage,
        )

        data: Dict[str, Any] = {
            "filename": job_id,
            "caption": caption,
            "content": method_content,
            "visual_intent": caption or "diagram",
            "additional_info": {"rounded_ratio": aspect_ratio, "image_size": image_size},
            "max_critic_rounds": effective_max_critic_rounds,
        }

        self._write_status(
            PaperBananaJob(
                job_id=job_id,
                status="running",
                progress=45,
                stage="processing",
                stage_message="Running inference",
            )
        )
        self._ensure_not_cancelled(job_id)
        result_data: Dict[str, Any] = asyncio.run(
            processor.process_single_query(data, do_eval=do_eval)
        )
        job_dir = self._job_dir(job_id)
        (job_dir / "result.json").write_text(
            json.dumps(result_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._ensure_not_cancelled(job_id)
        self._write_status(
            PaperBananaJob(
                job_id=job_id,
                status="running",
                progress=85,
                stage="saving",
                stage_message="Saving outputs",
            )
        )
        self._ensure_not_cancelled(job_id)

        image_field = result_data.get("eval_image_field")
        if not image_field:
            # Fallback: select the first available generated jpg field.
            fallback_keys = [
                key
                for key, val in result_data.items()
                if isinstance(val, str) and key.endswith("_base64_jpg") and len(val) > 100
            ]
            image_field = fallback_keys[0] if fallback_keys else None
        b64_jpg = result_data.get(image_field) if image_field else None
        if not b64_jpg:
            available_image_fields = [
                key
                for key, val in result_data.items()
                if isinstance(val, str) and key.endswith("_base64_jpg")
            ]
            raise ServiceError(
                f"PaperBanana did not produce image field: {image_field or 'N/A'}; "
                f"available fields: {available_image_fields}"
            )

        img_bytes = base64.b64decode(b64_jpg)
        out_path = job_dir / "output.jpg"
        out_path.write_bytes(img_bytes)
        self._ensure_not_cancelled(job_id)

        self._write_status(
            PaperBananaJob(
                job_id=job_id,
                status="succeeded",
                progress=100,
                stage="completed",
                output_image_path=str(out_path),
            )
        )

    def get_result_payload(self, job_id: str) -> Dict[str, Any]:
        job = self._read_status(job_id)

        if job.status == "succeeded":
            return {
                "id": job_id,
                "status": "succeeded",
                "progress": 100,
                "stage": job.stage or "completed",
                "stageMessage": job.stage_message or "图像生成完成",
                "model": "paperbanana",
                "results": [
                    {
                        "url": f"/api/paperbanana/file/{job_id}",
                        "content": "PaperBanana generated",
                    }
                ],
            }
        if job.status == "failed":
            return {
                "id": job_id,
                "status": "failed",
                "progress": 100,
                "stage": job.stage or "failed",
                "stageMessage": job.stage_message or "任务失败",
                "model": "paperbanana",
                "error": job.error or "unknown error",
                "failure_reason": job.error or "unknown error",
                "results": [],
            }

        return {
            "id": job_id,
            "status": "running",
            "progress": max(1, min(99, job.progress or 1)),
            "stage": job.stage or "processing",
            "stageMessage": job.stage_message or "处理中",
            "model": "paperbanana",
            "results": [],
        }

    def get_output_file(self, job_id: str) -> Path:
        job = self._read_status(job_id)
        if job.status != "succeeded" or not job.output_image_path:
            raise NotFoundError("Output not ready")
        p = Path(job.output_image_path)
        if not p.exists():
            raise NotFoundError("Output file missing")
        return p


_paper_banana_service: Optional[PaperBananaService] = None


def get_paper_banana_service() -> PaperBananaService:
    global _paper_banana_service
    if _paper_banana_service is None:
        _paper_banana_service = PaperBananaService()
    return _paper_banana_service
