# 项目结构说明

整理后的 SCIdrawer 项目结构

## 根目录文件
- `app.py` - Flask 主应用文件
- `requirements.txt` - Python 依赖
- `local_config.py` - 本地开发配置（可选）
- `.env.example` - 环境变量示例文件
- `README.md` - 项目说明
- `CLAUDE.md` - Claude Code 项目指南
- `APIDoc.md` - API 文档
- `DEPLOYMENT.md` - 部署说明
- `PROJECT_STRUCTURE.md` - 本文件，项目结构说明

## 目录结构

### `src/` - 源代码目录
```
src/
├── __init__.py
├── config.py              # 配置管理类
├── models/               # 数据库模型
│   ├── __init__.py
│   ├── base.py          # 基础模型类
│   ├── user.py          # 用户模型
│   ├── api_key.py       # API密钥模型
│   └── usage_stats.py   # 使用统计模型
├── services/            # 业务逻辑服务
│   ├── __init__.py
│   ├── auth.py          # 认证服务
│   ├── api_key_service.py  # API密钥服务
│   ├── ai_service.py    # AI服务
│   └── database.py      # 数据库连接管理
├── utils/               # 工具函数
│   ├── __init__.py
│   ├── encryption.py    # 加密工具
│   ├── validation.py    # 验证工具
│   └── errors.py        # 错误类
└── routes/              # 路由处理
    ├── __init__.py
    ├── auth_routes.py   # 认证路由
    ├── api_routes.py    # API路由
    └── decorators.py    # 装饰器
```

### `static/` - 静态文件
```
static/
├── css/                 # 样式文件
│   ├── main.css        # 主样式文件（导入其他模块）
│   ├── design-system.css  # 设计系统
│   ├── components.css  # 组件样式
│   ├── layout.css      # 布局样式
│   └── app.css         # 应用特定样式
└── js/                 # JavaScript文件
    ├── app.js          # 主应用逻辑
    └── api-service.js  # API服务调用
```

### `templates/` - HTML模板
```
templates/
├── index.html          # 主页面
└── login.html          # 登录页面
```

### `scripts/` - 部署和运维脚本
```
scripts/
├── deploy.sh           # 完整部署脚本
├── deploy_manual.sh    # 手动部署脚本
├── setup_on_server.sh  # 服务器端设置脚本
└── final_fix.sh        # 问题修复脚本
```

### `tests/` - 测试文件
```
tests/
└── test-ui.html        # UI测试页面
```

### `backup/` - 备份文件
```
backup/
└── index-new.html      # 旧版模板备份
```

### 运行时目录（不提交到Git）
- `data/` - 应用数据（数据库等）
- `__pycache__/` - Python字节码缓存
- `.venv/` - Python虚拟环境

## 开发说明

1. **环境设置**：复制 `.env.example` 为 `.env` 并配置环境变量
2. **依赖安装**：`pip install -r requirements.txt`
3. **运行应用**：`python app.py`
4. **部署**：参考 `scripts/` 目录中的部署脚本

## 架构设计

项目采用面向对象设计模式：
- 单例模式：配置、数据库、服务等
- 工厂模式：Flask应用创建
- 模型-服务-控制器：清晰的MVC架构
- 依赖注入：服务间解耦
- 装饰器模式：路由认证和错误处理
