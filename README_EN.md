<p align="center">
  <img src="./static/app-icon.png" alt="SCIdrawer Logo" width="120" />
</p>

# SCIdrawer

> An AI workspace for SCI figure creation: prompt-to-image, multi-stage workflows, and image-to-DrawIO conversion.

English | [中文](./README.md)

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)](https://flask.palletsprojects.com/)
[![Electron](https://img.shields.io/badge/Electron-Desktop-47848F?logo=electron&logoColor=white)](https://www.electronjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## Overview

SCIdrawer helps researchers move from idea to publication-ready figures faster by providing:
- Prompt and reference-image based figure generation
- PaperBanana workflow modes (retrieval, planning, critique, evaluation)
- Edit-Banana integration for image-to-`.drawio`
- Unified web and desktop experience

## Key Features

- **Figure generation workspace** with model/prompt/reference controls
- **Workflow mode switching** (`vanilla`, `planner`, `critic`, `full`)
- **API key and provider routing management**
- **Image-to-DrawIO export** for editable diagrams

## Quick Start

### 1) Backend (Flask)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:<PORT>` (code default is `5001`, common example uses `1200`).

### 2) Desktop (Electron)

```bash
cd electron
npm install
npm run start
```

## Configuration

Copy `.env.example` to `.env` and configure:
- `APP_SECRET_KEY`
- `APP_USERNAME` / `APP_PASSWORD`
- `NANO_BANANA_API_KEY`
- `NANO_BANANA_HOST` or `API_HOST`
- `PORT`, `DATA_DIR`, `DB_PATH`
- `EDIT_BANANA_ROOT` (optional)

## Project Structure

```text
src/                # Backend core (routes/services/models)
templates/          # Jinja2 templates
static/             # Frontend assets (css/js/icons)
electron/           # Desktop wrapper
integrations/       # PaperBanana / Edit-Banana integrations
tests/              # Lightweight UI test page
doc/                # Documentation and OSS governance files
```

## Development Quality

```bash
make lint
make format
make check
```

CI checks:
- `ruff check src app.py`
- `black --check src app.py`
- `python -m compileall src app.py`

## Documentation

- [Contributing](./doc/CONTRIBUTING.md)
- [Code of Conduct](./doc/CODE_OF_CONDUCT.md)
- [Security Policy](./doc/SECURITY.md)
- [Changelog](./doc/CHANGELOG.md)
- [Open Source Checklist](./doc/OPEN_SOURCE_CHECKLIST.md)
- [User Manual](./doc/USER_MANUAL.md)

## License

MIT. See [LICENSE](./LICENSE).
