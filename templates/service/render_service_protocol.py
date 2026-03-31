from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from app.contract_registry import load_contract_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--service-name', required=True)
    parser.add_argument('--output', default='service.manifest.rendered.yaml')
    args = parser.parse_args()

    bundle = load_contract_bundle()
    manifest = {
        'service': {
            'name': args.service_name,
            'protocol_version': bundle.packet_version,
            'ingress_mode': 'gate-first',
            'http_surfaces': [
                {'path': endpoint, 'mandatory': True if endpoint != '/metrics' else False}
                for endpoint in bundle.mandatory_endpoints + ('/metrics',)
                if endpoint not in {'/metrics'} or True
            ],
            'required_env': [{'name': item} for item in bundle.mandatory_service_env],
            'registration': {
                'required': True,
                'contract': 'contracts/node_registration_contract.yaml',
            },
            'packet_contract': 'contracts/packet_envelope_v1.yaml',
            'node_contract': 'contracts/conformant_node_contract.yaml',
        }
    }
    out = Path(args.output)
    out.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding='utf-8')
    print(f'[RENDERED] {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
