from __future__ import annotations

from pathlib import Path
import sys

import yaml


def load_manifest(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle)


def render(template: str, values: dict[str, str]) -> str:
    output = template
    for key, value in values.items():
        output = output.replace('{{ ' + key + ' }}', value)
        output = output.replace('{{' + key + '}}', value)
    return output


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: python templates/service/render_service.py <manifest> <output-dir>')

    manifest_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    manifest = load_manifest(manifest_path)

    service = manifest['service']
    execution = manifest['execution']
    registration = manifest['registration']

    values = {
        'SERVICE_NAME': service['service_name'],
        'PACKAGE_NAME': service['package_name'],
        'APP_MODULE': service['app_module'],
        'ACTIONS': ', '.join(execution['allowed_actions']),
        'PRIMARY_CAPABILITY_ID': registration['capability_descriptor']['capability_id'],
        'PRIMARY_CAPABILITY_SUMMARY': registration['capability_descriptor']['capability_summary'],
    }

    template_dir = Path(__file__).parent
    targets = {
        f"{service['package_name']}/app.py": 'app.py.tmpl',
        f"{service['package_name']}/handlers.py": 'handlers.py.tmpl',
        f"{service['package_name']}/payloads.py": 'payloads.py.tmpl',
        f"{service['package_name']}/README_SERVICE.md": 'README_SERVICE.md.tmpl',
    }

    for rel_target, template_name in targets.items():
        rendered = render((template_dir / template_name).read_text(encoding='utf-8'), values)
        target = out_dir / rel_target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding='utf-8')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
