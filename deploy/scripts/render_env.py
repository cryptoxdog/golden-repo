from __future__ import annotations

import sys

ALLOW = ("L9_", "HOST", "PORT", "APP_MODULE", "LOG_LEVEL", "GATE_", "SERVICE_DOMAIN")
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    if k.startswith(ALLOW) or k in ALLOW:
        print(f"{k}={v}")
