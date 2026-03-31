from __future__ import annotations

from app.config import get_config
from app.preflight import run_preflight
from database.init_db import apply_schema


def main() -> None:
    cfg = get_config()
    run_preflight(cfg)
    apply_schema(cfg.state_db_path)


if __name__ == "__main__":
    main()
