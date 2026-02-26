# Contributing to SCIdrawer

## Getting Started
1. Fork and clone the repository.
2. Create a feature branch: `git checkout -b feat/your-topic`.
3. Set up backend:
   - `python -m venv .venv`
   - `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate`
   - `pip install -r requirements.txt`
4. Optional desktop shell:
   - `cd electron && npm install && npm run start`

## Development Workflow
- Keep route handlers in `src/routes/` thin; place logic in `src/services/`.
- Update related docs when behavior changes (`README.md`, `USER_MANUAL.md`).
- Avoid unrelated refactors in the same PR.

## Code Quality
- Run formatting and lint checks before opening a PR:
  - `make format`
  - `make lint`
  - `make check`

## Pull Requests
- Use clear PR titles and include:
  - Problem statement
  - What changed
  - How to test
  - Screenshots for UI changes
- Link related issues (e.g., `Fixes #123`) when applicable.

## Commit Messages
- Prefer conventional style:
  - `feat: add provider health endpoint`
  - `fix: handle missing api key store`
  - `docs: update setup instructions`
