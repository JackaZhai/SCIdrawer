# Security Policy

## Supported Versions
Security fixes are applied to the latest `main` branch.

## Reporting a Vulnerability
- Do **not** open public issues for security vulnerabilities.
- Report privately to maintainers with:
  - Affected component/path
  - Reproduction steps
  - Impact assessment
  - Suggested fix (if available)

## Handling Secrets
- Never commit API keys, tokens, passwords, or `.env` files.
- Use `.env.example` as a template for local configuration.
- Keep runtime data (`data/`, SQLite files, logs) out of source control whenever possible.
