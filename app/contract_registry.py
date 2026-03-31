from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = REPO_ROOT / 'contracts'


class ContractLoadError(RuntimeError):
    pass


@dataclass(frozen=True)
class ContractBundle:
    packet_envelope: dict[str, Any]
    conformant_node: dict[str, Any]
    node_registration: dict[str, Any]

    @property
    def packet_version(self) -> str:
        return str(self.packet_envelope['protocol']['version'])

    @property
    def packet_types(self) -> tuple[str, ...]:
        values = self.packet_envelope['protocol']['packet_types']
        return tuple(str(v) for v in values)

    @property
    def mandatory_endpoints(self) -> tuple[str, ...]:
        endpoints = self.conformant_node['runtime_surfaces']['mandatory_http_surfaces']
        return tuple(str(v['path']) for v in endpoints)

    @property
    def mandatory_service_env(self) -> tuple[str, ...]:
        values = self.conformant_node['deployment']['required_environment_variables']
        return tuple(str(v) for v in values)

    @property
    def required_registration_fields(self) -> tuple[str, ...]:
        values = self.node_registration['registration_contract']['required_fields']
        return tuple(str(v) for v in values)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ContractLoadError(f'missing contract file: {path}')
    with path.open('r', encoding='utf-8') as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ContractLoadError(f'contract must be a YAML mapping: {path}')
    return loaded


@lru_cache
def load_contract_bundle(contracts_dir: Path | None = None) -> ContractBundle:
    directory = contracts_dir or CONTRACTS_DIR
    return ContractBundle(
        packet_envelope=_load_yaml(directory / 'packet_envelope_v1.yaml'),
        conformant_node=_load_yaml(directory / 'conformant_node_contract.yaml'),
        node_registration=_load_yaml(directory / 'node_registration_contract.yaml'),
    )
