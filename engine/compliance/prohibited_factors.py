from __future__ import annotations

PROHIBITED_FACTORS = frozenset({"ssn", "dob", "medical_record_number"})


def contains_prohibited_factors(payload: dict) -> bool:
    return any(key in PROHIBITED_FACTORS for key in payload)
