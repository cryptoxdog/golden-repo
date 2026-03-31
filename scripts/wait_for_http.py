from __future__ import annotations

import sys
import time
import httpx

if __name__ == "__main__":
    url = sys.argv[1]
    timeout = float(sys.argv[2])
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2)
            if r.status_code == 200:
                raise SystemExit(0)
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit(1)
