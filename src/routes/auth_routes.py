"""
认证路由
"""

from typing import Any

from flask import Blueprint, redirect, render_template, request, url_for

from ..services.api_key_service import get_api_key_service
from ..services.auth import get_auth_service

# 创建认证蓝图
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> Any:
    """登录页面"""
    auth_service = get_auth_service()
    error: str = ""

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        # 检查登录尝试
        allowed, lock_error = auth_service.check_login_attempts(username)
        if not allowed:
            return render_template("login.html", error=lock_error)

        # 验证凭证
        user_id = auth_service.verify_credentials(username, password)
        if user_id:
            # 登录成功
            auth_service.login_user(user_id, username)

            # 引导API密钥
            api_key_service = get_api_key_service()
            api_key_service.bootstrap_api_keys(user_id)

            next_url = request.args.get("next") or url_for("main.index")
            return redirect(next_url)
        else:
            # 登录失败
            error = auth_service.record_failed_attempt(username)

    return render_template("login.html", error=error)


@auth_bp.get("/logout")
def logout() -> Any:
    """登出"""
    auth_service = get_auth_service()
    auth_service.logout_user()
    return redirect(url_for("auth.login"))
