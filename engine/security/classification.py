from __future__ import annotations

ALLOWED_CLASSIFICATIONS = frozenset({"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"})


def validate_classification(classification: str) -> None:
    if classification not in ALLOWED_CLASSIFICATIONS:
        raise ValueError(f"Invalid classification {classification!r}. Allowed: {ALLOWED_CLASSIFICATIONS}")
