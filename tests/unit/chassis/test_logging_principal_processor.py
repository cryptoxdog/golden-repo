# --- L9_META ---
# l9_schema: 1
# origin: golden-repo
# engine: golden-repo
# layer: [test, unit]
# tags: [test, unit, chassis, logging, structlog, principal_id, pii, adr_0003]
# owner: platform
# status: active
# --- /L9_META ---
"""Unit tests for ``chassis.logging.hash_principal_id_processor``.

Coverage matrix:

* present + non-empty       → field is removed, hash is set
* present + empty string    → field is dropped (no hash emitted)
* present + non-string      → field is dropped (no hash emitted)
* absent                    → record is unchanged
* idempotent                → running twice yields the same record
* hash is deterministic     → same input → same output
* explicit hash preserved   → caller-supplied hash is not overwritten
"""

from __future__ import annotations

import hashlib

import pytest

from chassis.logging import (
    PRINCIPAL_ID_FIELD,
    PRINCIPAL_ID_HASH_FIELD,
    hash_principal_id_processor,
    install_pii_processors,
    assert_no_raw_principal_id,
)


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ── happy path ─────────────────────────────────────────────────────────


def test_present_non_empty_string_is_hashed_and_dropped() -> None:
    record = {"event": "request", PRINCIPAL_ID_FIELD: "user_alice"}
    out = hash_principal_id_processor(None, "info", record)
    assert PRINCIPAL_ID_FIELD not in out
    assert out[PRINCIPAL_ID_HASH_FIELD] == _sha256_hex("user_alice")
    assert out["event"] == "request"


def test_hash_is_deterministic_per_input() -> None:
    a = hash_principal_id_processor(None, "info", {PRINCIPAL_ID_FIELD: "user_alice"})
    b = hash_principal_id_processor(None, "info", {PRINCIPAL_ID_FIELD: "user_alice"})
    assert a[PRINCIPAL_ID_HASH_FIELD] == b[PRINCIPAL_ID_HASH_FIELD]


def test_different_inputs_produce_different_hashes() -> None:
    a = hash_principal_id_processor(None, "info", {PRINCIPAL_ID_FIELD: "user_alice"})
    b = hash_principal_id_processor(None, "info", {PRINCIPAL_ID_FIELD: "user_bob"})
    assert a[PRINCIPAL_ID_HASH_FIELD] != b[PRINCIPAL_ID_HASH_FIELD]


# ── absent / empty / non-string drop paths ────────────────────────────


def test_absent_is_no_op() -> None:
    record = {"event": "request"}
    out = hash_principal_id_processor(None, "info", record)
    assert out == {"event": "request"}
    assert PRINCIPAL_ID_HASH_FIELD not in out


def test_empty_string_is_dropped_without_hash() -> None:
    record = {"event": "request", PRINCIPAL_ID_FIELD: ""}
    out = hash_principal_id_processor(None, "info", record)
    assert PRINCIPAL_ID_FIELD not in out
    assert PRINCIPAL_ID_HASH_FIELD not in out


def test_none_value_is_dropped_without_hash() -> None:
    record = {"event": "request", PRINCIPAL_ID_FIELD: None}
    out = hash_principal_id_processor(None, "info", record)
    assert PRINCIPAL_ID_FIELD not in out
    assert PRINCIPAL_ID_HASH_FIELD not in out


def test_non_string_value_is_dropped_without_hash() -> None:
    record = {"event": "request", PRINCIPAL_ID_FIELD: 12345}
    out = hash_principal_id_processor(None, "info", record)
    assert PRINCIPAL_ID_FIELD not in out
    assert PRINCIPAL_ID_HASH_FIELD not in out


# ── idempotency ────────────────────────────────────────────────────────


def test_running_twice_is_idempotent() -> None:
    record = {"event": "request", PRINCIPAL_ID_FIELD: "user_alice"}
    once = hash_principal_id_processor(None, "info", dict(record))
    twice = hash_principal_id_processor(None, "info", dict(once))
    assert once == twice


def test_explicit_hash_field_is_preserved() -> None:
    explicit = "deadbeef" * 8
    record = {
        "event": "request",
        PRINCIPAL_ID_FIELD: "user_alice",
        PRINCIPAL_ID_HASH_FIELD: explicit,
    }
    out = hash_principal_id_processor(None, "info", record)
    assert PRINCIPAL_ID_FIELD not in out
    assert out[PRINCIPAL_ID_HASH_FIELD] == explicit


# ── chain installation ────────────────────────────────────────────────


def test_install_pii_processors_prepends_hashing_processor() -> None:
    def existing_processor(*_args, **_kwargs):
        return {}

    chain = install_pii_processors([existing_processor])
    assert chain[0] is hash_principal_id_processor
    assert chain[-1] is existing_processor


def test_install_pii_processors_does_not_mutate_input() -> None:
    initial: list = []
    chain = install_pii_processors(initial)
    assert initial == []
    assert chain != initial


# ── compliance guard ──────────────────────────────────────────────────


def test_assert_no_raw_principal_id_passes_when_field_absent() -> None:
    assert_no_raw_principal_id({"event": "request"})


def test_assert_no_raw_principal_id_passes_when_only_hash_present() -> None:
    assert_no_raw_principal_id(
        {"event": "request", PRINCIPAL_ID_HASH_FIELD: "abc"}
    )


def test_assert_no_raw_principal_id_passes_when_value_empty() -> None:
    assert_no_raw_principal_id({"event": "request", PRINCIPAL_ID_FIELD: ""})


def test_assert_no_raw_principal_id_fails_when_raw_value_present() -> None:
    with pytest.raises(AssertionError) as excinfo:
        assert_no_raw_principal_id(
            {"event": "request", PRINCIPAL_ID_FIELD: "user_alice"}
        )
    assert "compliance violation" in str(excinfo.value)
