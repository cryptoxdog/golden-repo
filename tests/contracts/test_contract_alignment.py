from __future__ import annotations

from pathlib import Path

from app.contract_registry import load_contract_bundle
from scripts.validate_contract_alignment import validate_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_contract_bundle_loads() -> None:
    bundle = load_contract_bundle(REPO_ROOT / 'contracts')
    assert bundle.packet_version == '1.1'
    assert '/v1/execute' in bundle.mandatory_endpoints
    assert 'supported_actions' in bundle.required_registration_fields


def test_service_manifest_aligns_to_contracts() -> None:
    validate_manifest(REPO_ROOT / 'templates' / 'service' / 'service.manifest.yaml')
