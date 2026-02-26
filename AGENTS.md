# Repository Guidelines

## Project Structure & Module Organization
- `app.py`: Flask entrypoint.
- `src/`: backend application code.
- `src/routes/`: HTTP endpoints and decorators.
- `src/services/`: business logic (AI calls, auth, API key handling, DB access).
- `src/models/`: data models and persistence-layer objects.
- `templates/`: Jinja2 HTML pages.
- `static/`: frontend assets (`css/`, `js/`, favicon/icons).
- `electron/`: desktop wrapper that launches Flask and opens the local app.
- `tests/`: UI smoke page (`tests/test-ui.html`).
- `deploy/`, `scripts/`, `docs/`: deployment helpers and documentation.

## Build, Test, and Development Commands
- Backend setup:
  - `python -m venv .venv`
  - `.venv\\Scripts\\activate` (Windows) or `source .venv/bin/activate` (Linux/macOS)
  - `pip install -r requirements.txt`
- Run Flask locally: `python app.py` (default port from config or `PORT`).
- Production-style run: `gunicorn -w 4 -b 0.0.0.0:${PORT:-5000} app:app`.
- Desktop app:
  - `cd electron`
  - `npm install`
  - `npm run start`

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indentation, `snake_case` for functions/variables, `PascalCase` for classes.
- JavaScript: `camelCase` for functions/variables, descriptive DOM IDs, keep page state centralized.
- Keep modules focused: route handlers stay thin; move logic into `src/services/`.
- Prefer small, targeted edits; avoid unrelated refactors in feature PRs.

## Testing Guidelines
- Current repo uses lightweight/manual testing (no formal pytest suite yet).
- Validate changes by:
  - launching `python app.py`,
  - checking main flows in UI (dashboard, image generation, API key management),
  - opening `tests/test-ui.html` for component-level smoke checks.
- If adding automated tests, place them under `tests/` and use `test_*.py` naming.

## Commit & Pull Request Guidelines
- Existing history mixes conventional commits (`feat:`, `refactor:`) and short Chinese summaries.
- Preferred format: `<type>: <brief summary>` (e.g., `feat: add provider health check`).
- PRs should include:
  - what changed and why,
  - affected paths/modules,
  - manual verification steps,
  - screenshots for UI updates.

## Security & Configuration Tips
- Do not commit real API keys or secrets.
- Use `.env.example` as a template and environment variables for runtime config (`APP_SECRET_KEY`, `PORT`, provider keys).
- Treat `data/` as runtime data (SQLite, job artifacts), not source code.
