from __future__ import annotations

from chassis.contract_enforcement import enforce_packet_contract, enforce_registration_contract


def test_packet_contract_accepts_canonical_shape() -> None:
    packet = {
        'header': {'schema_version': '1.1', 'packet_type': 'request'},
        'address': {},
        'tenant': {},
        'payload': {},
        'security': {},
        'governance': {},
        'delegation_chain': [],
        'hop_trace': [],
        'lineage': {},
        'attachments': [],
    }
    enforce_packet_contract(packet)


def test_registration_contract_accepts_required_fields() -> None:
    registration = {
        'node_id': 'buyer-match-01',
        'internal_url': 'http://buyer-match-01:8000',
        'supported_actions': ['match'],
        'health_endpoint': '/v1/health',
        'readiness_endpoint': '/v1/readiness',
        'priority_class': 'standard',
        'max_concurrent': 32,
        'capability_descriptor': {'domain_affinities': ['buyers']},
    }
    enforce_registration_contract(registration)
