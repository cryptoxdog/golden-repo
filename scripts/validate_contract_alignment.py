from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from app.contract_registry import load_contract_bundle


class AlignmentError(RuntimeError):
    pass


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise AlignmentError(f'{path} must contain a YAML mapping')
    return loaded


def validate_manifest(manifest_path: Path) -> None:
    bundle = load_contract_bundle()
    manifest = _load_yaml(manifest_path)

    manifest_protocol = str(manifest['service']['protocol_version'])
    if manifest_protocol != bundle.packet_version:
        raise AlignmentError(
            f'service.manifest protocol_version={manifest_protocol} does not match canonical protocol {bundle.packet_version}'
        )

    endpoints = {str(item['path']) for item in manifest['service']['http_surfaces']}
    expected_endpoints = set(bundle.mandatory_endpoints)
    if not expected_endpoints.issubset(endpoints):
        missing = sorted(expected_endpoints - endpoints)
        raise AlignmentError(f'service.manifest missing mandatory HTTP surfaces: {", ".join(missing)}')

    env_values = {str(item['name']) for item in manifest['service']['required_env']}
    required_env = set(bundle.mandatory_service_env)
    if not required_env.issubset(env_values):
        missing = sorted(required_env - env_values)
        raise AlignmentError(f'service.manifest missing required env vars: {", ".join(missing)}')


def validate_contract_files(root: Path) -> None:
    contracts_dir = root / 'contracts'
    required = [
        contracts_dir / 'packet_envelope_v1.yaml',
        contracts_dir / 'conformant_node_contract.yaml',
        contracts_dir / 'node_registration_contract.yaml',
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise AlignmentError(f'missing canonical contract files: {", ".join(missing)}')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-root', default='.', help='repository root to validate')
    parser.add_argument('--manifest', default='templates/service/service.manifest.yaml', help='service manifest path relative to repo root')
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    validate_contract_files(root)
    validate_manifest(root / args.manifest)
    print('[CONTRACT ALIGNMENT OK]')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
