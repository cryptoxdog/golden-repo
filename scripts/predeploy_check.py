from __future__ import annotations

import sys

from app.config import get_config
from app.preflight import run_preflight


def main() -> int:
    try:
        cfg = get_config()
        run_preflight(cfg)
        print("[PREDEPLOY CHECK OK]")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[PREDEPLOY CHECK FAILED] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
