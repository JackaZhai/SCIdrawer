"""
API路由
"""

from typing import Any

from flask import Blueprint, jsonify, render_template, request, send_file

from ..models.usage_stats import UsageStats
from ..services.ai_service import get_ai_service
from ..services.api_key_service import get_api_key_service
from ..services.auth import get_auth_service
from ..services.edit_banana_service import get_edit_banana_service
from ..services.paper_banana_service import get_paper_banana_service
from ..services.provider_config_service import get_provider_config_service
from .decorators import api_login_required, handle_api_errors, login_required

# 创建API蓝图
api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/profile")
@api_login_required
@handle_api_errors
def profile() -> Any:
    """获取用户资料"""
    auth_service = get_auth_service()
    api_key_service = get_api_key_service()

    user_id = auth_service.require_auth()
    api_key_service.bootstrap_api_keys(user_id)
    store = api_key_service.serialize_keys(user_id)
    has_key = any(item.get("isActive") for item in (store.get("keys") or []))
    active_value = api_key_service.get_active_api_key_value(user_id, provider="grsai")

    from ..config import get_config

    config = get_config()

    return jsonify(
        {
            "hasKey": bool(has_key),
            "activeKeyMask": api_key_service.encryption.mask_key(active_value),
            "apiHost": config.api_host,
            "activeBaseUrl": api_key_service.get_active_base_url(user_id, provider="grsai"),
            "usage": (
                UsageStats.get_by_user_id(user_id).to_dict()
                if user_id
                else {"totalCalls": 0, "lastUsedAt": None}
            ),
        }
    )


@api_bp.get("/keys")
@api_login_required
@handle_api_errors
def list_keys() -> Any:
    """列出API密钥"""
    auth_service = get_auth_service()
    api_key_service = get_api_key_service()

    user_id = auth_service.require_auth()
    api_key_service.bootstrap_api_keys(user_id)

    return jsonify(api_key_service.serialize_keys(user_id))


@api_bp.post("/keys")
@api_login_required
@handle_api_errors
def add_key() -> Any:
    """添加API密钥"""
    auth_service = get_auth_service()
    api_key_service = get_api_key_service()

    user_id = auth_service.require_auth()
    data = request.get_json(force=True, silent=True) or {}
    provider = (data.get("provider") or "grsai").strip()
    value = (data.get("value") or "").strip()
    name = (data.get("name") or "").strip()
    base_url = (data.get("baseUrl") or data.get("base_url") or "").strip()

    result = api_key_service.add_api_key(user_id, provider, value, name=name, base_url=base_url)
    return jsonify(result)


@api_bp.delete("/keys/<key_id>")
@api_login_required
@handle_api_errors
def delete_key(key_id: str) -> Any:
    """删除API密钥"""
    auth_service = get_auth_service()
    api_key_service = get_api_key_service()

    user_id = auth_service.require_auth()
    result = api_key_service.delete_api_key(user_id, key_id)
    return jsonify(result)


@api_bp.post("/keys/active")
@api_login_required
@handle_api_errors
def set_active_key() -> Any:
    """设置活动API密钥"""
    auth_service = get_auth_service()
    api_key_service = get_api_key_service()

    user_id = auth_service.require_auth()
    data = request.get_json(force=True, silent=True) or {}
    key_id = (data.get("id") or "").strip()

    result = api_key_service.set_active_key(user_id, key_id)
    return jsonify(result)


@api_bp.get("/credits")
@api_login_required
@handle_api_errors
def credits() -> Any:
    """获取账户余额/积分（使用当前 grsai Key）"""
    auth_service = get_auth_service()
    ai_service = get_ai_service()

    user_id = auth_service.get_current_user_id()
    result = ai_service.get_credits(user_id)
    return jsonify(result)


@api_bp.get("/model-status")
@api_login_required
@handle_api_errors
def model_status() -> Any:
    """获取模型状态（使用当前 grsai Key）"""
    auth_service = get_auth_service()
    ai_service = get_ai_service()

    user_id = auth_service.get_current_user_id()
    model = (request.args.get("model") or "").strip()
    result = ai_service.get_model_status(user_id, model)
    return jsonify(result)


@api_bp.get("/provider-configs")
@api_login_required
@handle_api_errors
def provider_configs() -> Any:
    """List provider model defaults."""
    auth_service = get_auth_service()
    svc = get_provider_config_service()

    user_id = auth_service.require_auth()
    return jsonify({"configs": svc.list_all(user_id)})


@api_bp.post("/provider-configs")
@api_login_required
@handle_api_errors
def upsert_provider_config() -> Any:
    """Upsert provider model defaults."""
    auth_service = get_auth_service()
    svc = get_provider_config_service()

    user_id = auth_service.require_auth()
    data = request.get_json(force=True, silent=True) or {}

    provider = (data.get("provider") or "grsai").strip()
    text_model = (data.get("textModel") or data.get("text_model") or "").strip()
    image_model = (data.get("imageModel") or data.get("image_model") or "").strip()

    result = svc.upsert(user_id, provider, text_model, image_model)
    return jsonify({"config": result})


@api_bp.post("/draw")
@api_login_required
@handle_api_errors
def draw() -> Any:
    """生成图像"""
    auth_service = get_auth_service()
    ai_service = get_ai_service()

    user_id = auth_service.get_current_user_id()
    data = request.get_json(force=True, silent=True) or {}

    result = ai_service.generate_image(user_id, data)
    return jsonify(result)


@api_bp.post("/result")
@api_login_required
@handle_api_errors
def result() -> Any:
    """获取图像生成结果"""
    auth_service = get_auth_service()
    ai_service = get_ai_service()

    user_id = auth_service.get_current_user_id()
    data = request.get_json(force=True, silent=True) or {}
    draw_id = (data.get("id") or "").strip()

    result = ai_service.get_image_result(user_id, draw_id)
    return jsonify(result)


@api_bp.post("/cancel")
@api_login_required
@handle_api_errors
def cancel_result() -> Any:
    """取消图像生成任务"""
    auth_service = get_auth_service()
    ai_service = get_ai_service()

    user_id = auth_service.get_current_user_id()
    data = request.get_json(force=True, silent=True) or {}
    draw_id = (data.get("id") or "").strip()

    result = ai_service.cancel_image_result(user_id, draw_id)
    return jsonify(result)


@api_bp.get("/edit-banana/status")
@api_login_required
@handle_api_errors
def edit_banana_status() -> Any:
    """Edit-Banana integration status."""
    service = get_edit_banana_service()
    return jsonify(service.get_status().to_dict())


@api_bp.post("/edit-banana/convert")
@api_login_required
@handle_api_errors
def edit_banana_convert() -> Any:
    """Upload an image and return a DrawIO (.drawio) file."""
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "请上传图片文件(file)"}), 400

    filename = file.filename
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in {"png", "jpg", "jpeg", "bmp", "tiff", "webp"}:
        return jsonify({"error": "仅支持图片格式: png/jpg/jpeg/bmp/tiff/webp"}), 400

    with_text = request.form.get("withText", "true").lower() != "false"
    with_refinement = request.form.get("withRefinement", "false").lower() == "true"

    import uuid
    from pathlib import Path

    from ..config import get_config

    cfg = get_config()
    upload_dir = Path(cfg.data_dir) / "edit_banana" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    upload_path = upload_dir / f"{uuid.uuid4().hex}.{ext}"
    file.save(str(upload_path))

    service = get_edit_banana_service()
    status = service.get_status()
    if with_text and not status.text_module_available:
        with_text = False
    output_path = service.convert_to_drawio(
        upload_path,
        with_text=with_text,
        with_refinement=with_refinement,
    )

    download_name = f"{Path(filename).stem}.drawio"
    return send_file(
        str(output_path),
        as_attachment=True,
        download_name=download_name,
        mimetype="application/xml",
        conditional=True,
        max_age=0,
    )


@api_bp.get("/paperbanana/file/<job_id>")
@api_login_required
@handle_api_errors
def paperbanana_file(job_id: str):
    """Download PaperBanana output image."""
    service = get_paper_banana_service()
    output_path = service.get_output_file(job_id)
    return send_file(
        str(output_path),
        mimetype="image/jpeg",
        conditional=True,
        max_age=0,
    )


# 创建主页面蓝图
main_bp = Blueprint("main", __name__)


@main_bp.get("/")
@login_required
def index() -> Any:
    """主页面"""
    from ..config import get_config

    config = get_config()
    auth_service = get_auth_service()
    api_key_service = get_api_key_service()

    user_id = auth_service.get_current_user_id()
    api_key_service.bootstrap_api_keys(user_id)
    has_api_key = bool(api_key_service.get_active_api_key_value(user_id))

    return render_template("index.html", api_host=config.api_host, has_api_key=has_api_key)


@main_bp.get("/manual")
def manual() -> Any:
    """用户手册"""
    return render_template("manual.html")
