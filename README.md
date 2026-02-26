<p align="center">
  <img src="./static/app-icon.png" alt="SCIdrawer Logo" width="120" />
</p>
<p align="center"><em>"Vibe your chart like vibing code."</em></p>

# SCIdrawer

> 面向 SCI 科研绘图的 AI 工作台：提示词生图 + 多阶段流程 + 图片转 DrawIO。

[English](./README_EN.md) | 中文

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/) [![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)](https://flask.palletsprojects.com/) [![Electron](https://img.shields.io/badge/Electron-Desktop-47848F?logo=electron&logoColor=white)](https://www.electronjs.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE) 

## 项目简介

SCIdrawer 用于缩短科研绘图从“想法”到“可投稿图”的路径，提供：

- 文本/参考图驱动的科研插图生成；
- PaperBanana 多阶段流程（检索、规划、审图、评估）；
- Edit-Banana 集成：图片转 `.drawio`；
- Web + Electron 桌面一体化使用体验。

## 主要功能

- **图像生成工作台**：提示词、模型、参考图统一控制。
- **流程模式切换**：支持 `vanilla`、`planner`、`critic`、`full` 等。
- **模型与密钥管理**：支持多供应商路由与密钥切换。
- **图片转 DrawIO**：上传图片后导出结构化流程图文件。

## 快速开始

### 1) 后端启动（Flask）

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

访问：`http://127.0.0.1:<PORT>`（代码默认 `5001`，示例常用 `1200`）。

### 2) 桌面启动（Electron）

```bash
cd electron
npm install
npm run start
```

## 环境配置

复制 `.env.example` 为 `.env`，重点配置：

- `APP_SECRET_KEY`
- `APP_USERNAME` / `APP_PASSWORD`
- `NANO_BANANA_API_KEY`
- `NANO_BANANA_HOST` 或 `API_HOST`
- `PORT`, `DATA_DIR`, `DB_PATH`
- `EDIT_BANANA_ROOT`（可选）

## 目录结构

```text
src/                # 后端核心（routes/services/models）
templates/          # Jinja2 页面模板
static/             # 前端资源（css/js/icons）
electron/           # 桌面壳
integrations/       # PaperBanana / Edit-Banana 集成
tests/              # 轻量 UI 测试页
doc/                # 文档与开源规范
```

## 开发与质量

```bash
make lint
make format
make check
```

CI 默认检查：

- `ruff check src app.py`
- `black --check src app.py`
- `python -m compileall src app.py`

## 文档

- [贡献指南](./doc/CONTRIBUTING.md)
- [行为准则](./doc/CODE_OF_CONDUCT.md)
- [安全策略](./doc/SECURITY.md)
- [变更日志](./doc/CHANGELOG.md)
- [开源检查清单](./doc/OPEN_SOURCE_CHECKLIST.md)
- [用户手册](./doc/USER_MANUAL.md)

## 许可证

MIT，见 [LICENSE](./LICENSE)。
