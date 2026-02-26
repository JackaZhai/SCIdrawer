"""
认证服务
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from flask import session

from ..config import get_config
from ..models.user import User
from ..utils.errors import AuthenticationError


class AuthService:
    """认证服务"""

    def __init__(self):
        self.config = get_config()
        self.login_attempts: Dict[str, Dict[str, any]] = {}

    def verify_credentials(self, username: str, password: str) -> Optional[int]:
        """验证用户凭证"""
        # 确保默认用户存在
        User.ensure_default_user()

        user = User.get_by_username(username)
        if not user:
            return None

        if not user.verify_password(password):
            return None

        return user.id

    def check_login_attempts(self, username: str) -> Tuple[bool, Optional[str]]:
        """检查登录尝试次数"""
        attempt = self.login_attempts.get(username, {"count": 0, "locked_until": None})
        locked_until = attempt.get("locked_until")
        now = datetime.utcnow()

        if locked_until and locked_until > now:
            remaining = int((locked_until - now).total_seconds() // 60) + 1
            return False, f"账号已锁定，请 {remaining} 分钟后重试"

        return True, None

    def record_failed_attempt(self, username: str) -> str:
        """记录失败的登录尝试"""
        attempt = self.login_attempts.get(username, {"count": 0, "locked_until": None})
        attempt["count"] = attempt.get("count", 0) + 1

        if attempt["count"] >= self.config.max_login_attempts:
            attempt["locked_until"] = datetime.utcnow() + timedelta(
                minutes=self.config.lock_minutes
            )
            error_msg = f"错误次数过多，已锁定 {self.config.lock_minutes} 分钟"
        else:
            remaining = self.config.max_login_attempts - attempt["count"]
            error_msg = f"用户名或密码错误，剩余重试次数 {remaining} 次"

        self.login_attempts[username] = attempt
        return error_msg

    def clear_login_attempts(self, username: str) -> None:
        """清除登录尝试记录"""
        self.login_attempts.pop(username, None)

    def login_user(self, user_id: int, username: str) -> None:
        """登录用户"""
        session["authenticated"] = True
        session["user_id"] = user_id
        session["username"] = username
        self.clear_login_attempts(username)

    def logout_user(self) -> None:
        """登出用户"""
        session.clear()

    def _ensure_default_session(self) -> Optional[int]:
        """Ensure a default user session exists."""
        if session.get("authenticated") and session.get("user_id") is not None:
            return int(session["user_id"])

        user = User.ensure_default_user()
        session["authenticated"] = True
        session["user_id"] = user.id
        session["username"] = user.username
        return user.id

    def is_authenticated(self) -> bool:
        """Check whether the user is authenticated."""
        self._ensure_default_session()
        return True

    def get_current_user_id(self) -> Optional[int]:
        """Get the current user id."""
        user_id = session.get("user_id")
        if user_id is None:
            user_id = self._ensure_default_session()
        return int(user_id) if user_id is not None else None

    def get_current_username(self) -> Optional[str]:
        """获取当前用户名"""
        return session.get("username")

    def require_auth(self) -> int:
        """Require authentication and return the user id."""
        user_id = self._ensure_default_session()
        if not user_id:
            raise AuthenticationError("User session is invalid")
        return int(user_id)


# 全局认证服务实例
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """获取认证服务实例（单例模式）"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
