# Open Source Release Checklist

## Must-Have
- [ ] `LICENSE` selected and reviewed
- [ ] `README.md` quick start is accurate
- [ ] `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` published
- [ ] `SECURITY.md` published
- [ ] CI passes on pull requests (`ruff`, `black --check`, `compileall`)

## Repository Hygiene
- [ ] Runtime artifacts are not tracked (`data/`, logs, local DB, secrets)
- [ ] `.gitignore` covers generated files and local envs
- [ ] `data/.gitkeep` and `logs/.gitkeep` preserved for directory structure
- [ ] No hardcoded API keys or private endpoints in tracked files

## Developer Experience
- [ ] One-command checks available (`make check`)
- [ ] Formatting/lint config present (`pyproject.toml`, `.editorconfig`)
- [ ] PR template exists (`.github/PULL_REQUEST_TEMPLATE.md`)
- [ ] Changelog policy defined (`CHANGELOG.md`)

## Before Publishing
- [ ] Run clean-environment validation (fresh venv install + checks)
- [ ] Validate desktop wrapper startup (`electron/npm run start`)
- [ ] Tag an initial open-source release (e.g., `v1.0.0`)
