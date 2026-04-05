from __future__ import annotations

from pathlib import Path

from chassis.contract_enforcement import enforce_packet_contract
from chassis.types import PacketEnvelope, Payload, TenantInfo

CONTRACTS_DIR = str(Path(__file__).resolve().parents[2] / "contracts")


def make_packet() -> PacketEnvelope:
    return PacketEnvelope(
        source_node="alpha",
        target_node="beta",
        tenant=TenantInfo(tenant_id="t1", actor="igor", originator="igor", org_id="org"),
        payload=Payload(action="execute", data={"x": 1}),
    )


def test_valid_packet_has_no_violations() -> None:
    assert enforce_packet_contract(make_packet(), contracts_dir=CONTRACTS_DIR) == []


def test_missing_fields_are_reported() -> None:
    packet = make_packet()
    packet.source_node = ""
    violations = enforce_packet_contract(packet, contracts_dir=CONTRACTS_DIR)
    assert "source_node is empty" in violations


def test_schema_version_mismatch_is_reported() -> None:
    packet = make_packet()
    packet.schema_version = "9.9"
    violations = enforce_packet_contract(packet, contracts_dir=CONTRACTS_DIR)
    assert any("schema_version mismatch" in violation for violation in violations)
