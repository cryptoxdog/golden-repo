#!/usr/bin/env bash
set -euo pipefail
git diff --name-only "${1:-HEAD~1}...${2:-HEAD}"
