from __future__ import annotations

import pytest
from chassis.contract_enforcement import ContractViolation, enforce_packet_contract
from chassis.types import TenantSection, build_root_packet


def _pkt():
    return build_root_packet(
        source_node="gw", destination_node="engine", action="execute",
        tenant=TenantSection(actor="u", on_behalf_of="u", originator="gw", org_id="org"),
        payload={"k": "v"},
    )


def test_valid_packet_passes():
    enforce_packet_contract(_pkt())


def test_tampered_payload_fails():
    pkt = _pkt()
    pkt.payload["injected"] = "evil"
    with pytest.raises(ContractViolation, match="content_hash"):
        enforce_packet_contract(pkt)


def test_empty_source_node_fails():
    pkt = _pkt()
    object.__setattr__(pkt, "source_node", "")
    with pytest.raises(ContractViolation):
        enforce_packet_contract(pkt)
