"""Readiness for the focused printable demonstrator."""
from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/python'))


def readiness():
    checks = {name: importlib.util.find_spec(name) is not None for name in ('numpy', 'scipy', 'trimesh','cantera')}
    for name, path in {'dotnet': '.tools/dotnet/dotnet.exe',
                       'bridge': 'integrations/bin/Release/net9.0/Vega.Native.dll',
                       'kernel': 'integrations/bin/Release/net9.0/picogk.26.2.dll'}.items():
        checks[name] = (ROOT / path).is_file()
    return dict(ready=all(checks.values()), scope='SABRE-inspired precooled combined-cycle geometry study', checks=checks)


if __name__ == '__main__':
    report = readiness()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['ready'] else 1)
