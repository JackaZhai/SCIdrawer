"""
错误类定义
"""

from typing import Optional


class ApiError(Exception):
    """API错误异常类"""

    def __init__(self, message: str, status_code: int = 500, details: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {"error": self.message}
        if self.details:
            result["details"] = self.details
        return result


class AuthenticationError(ApiError):
    """认证错误"""

    def __init__(self, message: str = "认证失败", details: Optional[str] = None):
        super().__init__(message, status_code=401, details=details)


class ValidationError(ApiError):
    """验证错误"""

    def __init__(self, message: str = "验证失败", details: Optional[str] = None):
        super().__init__(message, status_code=400, details=details)


class NotFoundError(ApiError):
    """未找到错误"""

    def __init__(self, message: str = "未找到资源", details: Optional[str] = None):
        super().__init__(message, status_code=404, details=details)


class ServiceError(ApiError):
    """服务错误"""

    def __init__(self, message: str = "服务内部错误", details: Optional[str] = None):
        super().__init__(message, status_code=500, details=details)
