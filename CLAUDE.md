# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

a.zhai's ToolBox is a Flask web application that provides a web interface for AI image generation and chat completion services. It acts as a middleware between users and an upstream AI API service (GRSAI).

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Activate virtual environment (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Development mode (listens on all interfaces)
python app.py

# Production mode with Gunicorn
gunicorn -w 4 -b 0.0.0.0:${PORT:-5000} app:app
```

### Environment Variables
The application uses the following environment variables (set in `.env` or system environment):
- `APP_SECRET_KEY`: Flask session secret key (required)
- `APP_USERNAME`: Initial admin username (default: "admin")
- `APP_PASSWORD`: Initial admin password (default: "banana123")
- `NANO_BANANA_API_KEY`: API key for upstream service
- `NANO_BANANA_HOST`: Upstream API host (default: "https://api.grsai.com")
- `PORT`: Server port (default: 5000)
- `DATA_DIR`: Data storage directory (default: "data")
- `DB_PATH`: SQLite database path (default: "data/app.db")
- `MAX_LOGIN_ATTEMPTS`: Maximum failed login attempts before lockout (default: 5)
- `LOCK_MINUTES`: Lockout duration in minutes (default: 10)

## Architecture (面向对象重构版本)

### 项目结构
```
nano_banana/
├── app.py                    # 主应用文件（Flask工厂模式）
├── local_config.py           # 本地配置文件（可选，开发用）
├── requirements.txt
├── README.md
├── CLAUDE.md
├── .gitignore
├── __pycache__/
├── src/                      # 源代码目录
│   ├── __init__.py
│   ├── config.py            # 配置管理类
│   ├── models/              # 数据库模型
│   │   ├── __init__.py
│   │   ├── base.py          # 基础模型类
│   │   ├── user.py          # 用户模型
│   │   ├── api_key.py       # API密钥模型
│   │   └── usage_stats.py   # 使用统计模型
│   ├── services/            # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── auth.py          # 认证服务
│   │   ├── api_key_service.py  # API密钥服务
│   │   ├── ai_service.py    # AI服务
│   │   └── database.py      # 数据库连接管理
│   ├── utils/               # 工具函数
│   │   ├── __init__.py
│   │   ├── encryption.py    # 加密工具
│   │   ├── validation.py    # 验证工具
│   │   └── errors.py        # 错误类
│   └── routes/              # 路由处理
│       ├── __init__.py
│       ├── auth_routes.py   # 认证路由
│       ├── api_routes.py    # API路由
│       └── decorators.py    # 装饰器
└── data/                    # 数据目录（运行时创建）
```

### 核心设计模式
1. **单例模式**: 配置、数据库、服务等使用单例确保全局唯一实例
2. **工厂模式**: Flask应用使用工厂函数 `create_app()` 创建
3. **模型-服务-控制器**: 清晰的MVC架构分离
4. **依赖注入**: 服务间通过依赖注入解耦
5. **装饰器模式**: 路由使用装饰器处理认证和错误

### 核心组件说明

#### 1. 配置管理 (`src/config.py`)
- `Config` 类：统一管理所有配置，支持环境变量 > 本地配置 > 默认值的优先级
- 单例模式：通过 `get_config()` 获取全局唯一配置实例

#### 2. 数据库模型 (`src/models/`)
- `BaseModel`：所有模型的基类，定义表结构和CRUD操作接口
- `User`：用户模型，处理用户认证和密码加密
- `ApiKey`：API密钥模型，支持加密存储和密钥管理
- `UsageStats`：使用统计模型，记录用户调用次数和时间

#### 3. 业务服务 (`src/services/`)
- `DatabaseManager`：数据库连接管理，提供上下文管理器
- `AuthService`：认证服务，处理登录、会话和权限验证
- `ApiKeyService`：API密钥服务，管理密钥的加密、解密和激活状态
- `AIService`：AI服务，封装上游API调用和流式处理

#### 4. 工具类 (`src/utils/`)
- `EncryptionService`：加密服务，处理API密钥的加密解密
- `ValidationService`：验证服务，统一验证输入数据
- 错误类：`ApiError`, `AuthenticationError`, `ValidationError` 等

#### 5. 路由处理 (`src/routes/`)
- `auth_routes.py`：认证相关路由（登录、登出）
- `api_routes.py`：API路由和主页面路由
- `decorators.py`：路由装饰器（登录要求、错误处理）

### 数据库架构
应用使用SQLite，包含三个主要表：
- `users`：用户认证（用户名、密码哈希、盐值）
- `api_keys`：加密的API密钥，支持来源跟踪
- `usage_stats`：用户调用统计和最后使用时间

### 安全特性
- 密码哈希：PBKDF2-HMAC-SHA256 + 随机盐值
- API密钥加密：Fernet对称加密
- 登录尝试限制和账户锁定
- 基于会话的认证

### API集成
应用代理请求到以下上游端点：
- `{API_HOST}/v1/draw/nano-banana`：图像生成
- `{API_HOST}/v1/draw/result`：图像生成结果查询
- `{API_HOST}/v1/chat/completions`：聊天完成

## Development Notes

### Database Initialization
The database is automatically initialized on first run via `init_db()` function. The default admin user is created if it doesn't exist.

### API Key Management
- API keys are encrypted before storage
- Multiple keys can be managed per user
- One active key is selected for API calls
- Keys from environment variables are automatically added to user's key store

### File Structure
```
nano_banana/
├── app.py              # Main Flask application
├── config.py           # Local configuration (optional)
├── requirements.txt    # Python dependencies
├── README.md           # Deployment instructions
├── .gitignore          # Git ignore rules
├── data/               # Runtime data (created automatically)
│   └── app.db         # SQLite database
└── __pycache__/       # Python bytecode cache
```

### Testing
No test framework is currently configured. Manual testing can be done by:
1. Starting the application
2. Accessing `http://localhost:5000`
3. Logging in with admin credentials
4. Testing image generation and chat features

### Deployment Considerations
- Use Gunicorn or similar WSGI server for production
- Set strong `APP_SECRET_KEY` for session security
- Configure proper firewall rules for external access
- Monitor database growth in `data/app.db`
- Implement regular backups of the data directory