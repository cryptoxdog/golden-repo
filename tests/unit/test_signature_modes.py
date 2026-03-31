from __future__ import annotations

import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from chassis.packet_envelope import create_packet
from chassis.security import export_ed25519_public_key, sign_packet, verify_signature


def test_hmac_roundtrip(monkeypatch):
    monkeypatch.setenv('L9_VERIFYING_KEYS_JSON', '{"k1":"shared-secret"}')
    monkeypatch.setenv('L9_SIGNING_KEY_ID', 'k1')
    from app.config import get_config
    get_config.cache_clear()
    pkt = create_packet('healthcheck', {'detail': False}, 'acme', 'svc')
    signed = sign_packet(pkt, key='shared-secret', key_id='k1', algorithm='hmac-sha256')
    assert verify_signature(signed)


def test_ed25519_roundtrip(monkeypatch):
    priv = Ed25519PrivateKey.generate()
    priv_b64 = base64.b64encode(priv.private_bytes_raw()).decode('ascii')
    pub_b64 = export_ed25519_public_key(priv_b64)
    monkeypatch.setenv('L9_VERIFYING_KEYS_JSON', '{"n1":"' + pub_b64 + '"}')
    from app.config import get_config
    get_config.cache_clear()
    pkt = create_packet('healthcheck', {'detail': False}, 'acme', 'svc')
    signed = sign_packet(pkt, key=priv_b64, key_id='n1', algorithm='ed25519')
    assert verify_signature(signed)
