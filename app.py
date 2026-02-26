"""
SCIdrawer - AI Service Middleware
面向对象重构版本
"""

import os

from flask import Flask

from src.config import get_config
from src.routes.api_routes import api_bp, main_bp


def create_app() -> Flask:
    """创建Flask应用"""
    config = get_config()

    # 创建Flask应用
    app = Flask(__name__)
    app.secret_key = config.app_secret_key
    app.config["JSON_AS_ASCII"] = False

    # 注册蓝图
    app.register_blueprint(api_bp)
    app.register_blueprint(main_bp)

    @app.after_request
    def add_header(response):
        """Add headers to both force latest IE rendering engine or Chrome Frame,
        and also to cache the rendered page for 10 minutes.
        """
        if "Content-Type" in response.headers:
            if "application/javascript" in response.headers["Content-Type"]:
                response.headers["Content-Type"] = "application/javascript; charset=utf-8"
            elif "text/css" in response.headers["Content-Type"]:
                response.headers["Content-Type"] = "text/css; charset=utf-8"
        return response

    # 确保默认用户存在
    from src.models.user import User

    User.ensure_default_user()

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    config = get_config()
    port = int(os.getenv("PORT", str(config.port)))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
