# AI Coding Context — L9 Golden Repo

## Architecture
- FastAPI service with `/health` and `/v1/execute` as primary endpoints
- Settings via Pydantic `BaseSettings` — all config from `.env`
- `engine/` = service logic; `tests/` = pytest suite

## Rules
- All public functions require type hints
- No hardcoded secrets — use `Settings` class
- No bare `except` — always specify exception type
- Async IO for all network/DB operations
- Use `structlog` for logging (not `print`)

## Protected Files — Get Approval Before Modifying
- `engine/settings.py` — settings schema
- `docker-compose.prod.yml` — production infrastructure
- `.github/workflows/ci-quality.yml` — CI gate

## Anti-Patterns to Flag
- Hardcoded API keys or secrets
- Synchronous blocking calls in async functions
- Direct subprocess calls without validation
- Missing error handling on external API calls
