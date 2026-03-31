from __future__ import annotations

import ipaddress
import sys

REQ = ["DO_API_TOKEN", "DO_REGION", "SSH_PUBLIC_KEY", "ADMIN_IP_CIDR", "SERVICE_NAME", "APP_MODULE", "L9_ENVIRONMENT", "L9_RUNTIME_MODE"]

def parse(path: str) -> dict[str, str]:
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out

if __name__ == "__main__":
    env = parse(sys.argv[1])
    for k in REQ:
        if not env.get(k):
            raise SystemExit(f"missing required value: {k}")
    ipaddress.ip_network(env["ADMIN_IP_CIDR"], strict=False)
    if env["L9_ENVIRONMENT"] != "prod":
        raise SystemExit("L9_ENVIRONMENT must be prod")
    if env["L9_RUNTIME_MODE"] != "single-node":
        raise SystemExit("L9_RUNTIME_MODE must be single-node")
    print("[DEPLOY ENV OK]")
