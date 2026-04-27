#!/usr/bin/env python3
"""Enforce the L9_META header on every doc and contract artifact.

Scope:
  * docs/**/*.md
  * contracts/**/*.yaml (contracts and contract docs)
  * Any directory README.md added by the L9 scaffold.

Accepted header forms:
  * Markdown inline:  `<!-- L9_META: ... -->`
  * Markdown block:   `<!-- L9_META\\n key: value\\n /L9_META -->` (the canonical form)
  * YAML inline:      `# L9_META: ...`
  * YAML block:       `# --- L9_META ---\\n# key: value\\n# --- /L9_META ---` (the canonical form)

Files explicitly listed in EXEMPTIONS are skipped (legacy or third-party
artifacts that pre-date the L9 scaffold).

Tolerant mode:
  * If `docs/` and `contracts/` are both empty of in-scope files, exit 0.
  * Files that fail are reported with their path and the reason.

Exit codes:
  0 = all in-scope files have the header (or none in scope).
  1 = one or more files missing the header.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Look for the header within the first ~80 lines of the file. The block-form
# Markdown header in this repo can take up to ~10 lines on its own.
HEADER_WINDOW_LINES = 80

# Markdown forms.
MD_INLINE_RE = re.compile(r"<!--\s*L9_META\s*:")
MD_BLOCK_OPEN_RE = re.compile(r"<!--\s*\n?\s*L9_META\b")
MD_BLOCK_CLOSE_RE = re.compile(r"/L9_META\s*-->")

# YAML forms.
YAML_INLINE_RE = re.compile(r"^\s*#\s*L9_META\s*:", re.MULTILINE)
YAML_BLOCK_OPEN_RE = re.compile(r"^\s*#\s*-{2,}\s*L9_META\s*-{2,}\s*$", re.MULTILINE)
YAML_BLOCK_CLOSE_RE = re.compile(r"^\s*#\s*-{2,}\s*/L9_META\s*-{2,}\s*$", re.MULTILINE)

# Files that pre-date the L9 scaffold and are not required to carry the header.
# Paths are POSIX-style relative to repo root.
EXEMPTIONS: set[str] = {
    # Legacy contract docs already covered by other quality gates.
    "docs/contracts/TEST_QUALITY.md",
    "docs/contracts/QUERY_PERFORMANCE.md",
    "docs/contracts/LOG_SAFETY.md",
    "docs/contracts/API_REGRESSION.md",
    # Top-level legacy contract YAMLs (kept during the migration window).
    "contracts/packet_envelope_v1.yaml",
    "contracts/conformant_node_contract.yaml",
    "contracts/node_registration_contract.yaml",
    "contracts/HEALTHCHECK_READINESS_SPEC.md",
    "contracts/conformance_checklist.md",
}

# Path prefixes (relative to repo root, POSIX-style) that are exempt as a whole.
# These directories pre-date the L9 scaffold; they are tracked for backfill in
# a separate ticket and are explicitly out of scope for this gate.
EXEMPT_PREFIXES: tuple[str, ...] = (
    "docs/agent-tasks/",
    "docs/audit/",
    "docs/review/",
)


def _read_window(path: Path) -> str:
    """Read the first HEADER_WINDOW_LINES lines of a file."""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        lines: list[str] = []
        for i, line in enumerate(handle):
            if i >= HEADER_WINDOW_LINES:
                break
            lines.append(line)
    return "".join(lines)


def _iter_targets() -> list[Path]:
    targets: list[Path] = []

    docs_dir = REPO_ROOT / "docs"
    if docs_dir.exists():
        targets.extend(p for p in docs_dir.rglob("*.md") if p.is_file())

    contracts_dir = REPO_ROOT / "contracts"
    if contracts_dir.exists():
        targets.extend(p for p in contracts_dir.rglob("*.yaml") if p.is_file())
        targets.extend(p for p in contracts_dir.rglob("*.md") if p.is_file())

    return sorted(targets)


def _is_exempt(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    if rel in EXEMPTIONS:
        return True
    return any(rel.startswith(prefix) for prefix in EXEMPT_PREFIXES)


def _md_has_header(text: str) -> bool:
    if MD_INLINE_RE.search(text):
        return True
    open_match = MD_BLOCK_OPEN_RE.search(text)
    if not open_match:
        return False
    close_match = MD_BLOCK_CLOSE_RE.search(text, pos=open_match.end())
    return bool(close_match)


def _yaml_has_header(text: str) -> bool:
    if YAML_INLINE_RE.search(text):
        return True
    open_match = YAML_BLOCK_OPEN_RE.search(text)
    if not open_match:
        return False
    close_match = YAML_BLOCK_CLOSE_RE.search(text, pos=open_match.end())
    return bool(close_match)


def _check(path: Path) -> tuple[bool, str]:
    head = _read_window(path)
    suffix = path.suffix.lower()
    if suffix == ".md":
        ok = _md_has_header(head)
        return ok, "missing L9_META block (inline `<!-- L9_META: ... -->` or block `<!-- L9_META ... /L9_META -->`)"
    if suffix in {".yaml", ".yml"}:
        ok = _yaml_has_header(head)
        return ok, "missing L9_META block (inline `# L9_META:` or block `# --- L9_META --- ... # --- /L9_META ---`)"
    return True, "unsupported suffix; skipped"


def main() -> int:
    print("=" * 64)
    print("L9 Header Compliance")
    print("=" * 64)

    targets = _iter_targets()
    if not targets:
        print("NOTE: no docs/ or contracts/ targets found; nothing to check.")
        print("RESULT: PASS")
        return 0

    fails: list[str] = []
    skips: list[str] = []
    passes = 0

    for path in targets:
        rel = path.relative_to(REPO_ROOT)
        if _is_exempt(path):
            skips.append(f"SKIP: {rel} (exempt)")
            continue
        ok, reason = _check(path)
        if ok:
            passes += 1
        else:
            fails.append(f"FAIL: {rel} :: {reason}")

    for line in skips:
        print(f"  {line}")
    for line in fails:
        print(f"  {line}")

    print()
    print(f"Files checked: {len(targets) - len(skips)}")
    print(f"Passes:        {passes}")
    print(f"Skips:         {len(skips)}")
    print(f"Failures:      {len(fails)}")

    if fails:
        print()
        print("RESULT: FAIL -- one or more files missing the L9_META header")
        return 1

    print()
    print("RESULT: PASS -- L9_META present on every in-scope file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
