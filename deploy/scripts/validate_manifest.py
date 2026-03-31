from __future__ import annotations

from pathlib import Path
import sys

from scripts.validate_contract_alignment import validate_manifest


def main() -> int:
    manifest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('templates/service/service.manifest.yaml')
    validate_manifest(manifest)
    print('[MANIFEST OK]')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
