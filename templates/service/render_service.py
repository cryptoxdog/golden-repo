from __future__ import annotations

from pathlib import Path
import sys


TEMPLATES = {
    "app.py": "app.py.tmpl",
    "handlers.py": "handlers.py.tmpl",
    "payloads.py": "payloads.py.tmpl",
    "README.md": "README_SERVICE.md.tmpl",
}


def main(name: str) -> None:
    package = name.replace('-', '_')
    base = Path(package)
    base.mkdir(parents=True, exist_ok=True)
    tpl_dir = Path(__file__).parent
    for out_name, tpl_name in TEMPLATES.items():
        content = (tpl_dir / tpl_name).read_text(encoding='utf-8')
        content = content.replace('__SERVICE_NAME__', name).replace('__PACKAGE_NAME__', package)
        (base / out_name).write_text(content, encoding='utf-8')
    print(base)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: python templates/service/render_service.py <service-name>')
    main(sys.argv[1])
