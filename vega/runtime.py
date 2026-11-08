"""Dependency readiness for the actual export pipeline, without importing CAD stacks together."""
from functools import lru_cache
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def readiness():
    checks = {}
    groups = {
        'python': ['numpy', 'scipy.optimize', 'rocketcea.cea_obj', 'proptools.nozzle', 'trimesh'],
        'cadquery': ['cadquery'],
        'build123d': ['build123d'],
        'meshing': ['gmsh'],
    }
    for target, modules in groups.items():
        # CAD packages use different OpenCASCADE bindings. Probe in isolation,
        # exactly as reference_cad.py does during a real export.
        code = ('import sys,importlib,json; sys.path.insert(0,sys.argv[1]); '
                'mods=json.loads(sys.argv[2]); '
                '[importlib.import_module(m) for m in mods]')
        try:
            result = subprocess.run([sys.executable, '-c', code, str(ROOT/'.tools'/target),
                                     json.dumps(modules)], capture_output=True, text=True, timeout=45)
            checks[target] = {'ready': result.returncode == 0}
            if result.returncode:
                checks[target]['error'] = result.stderr[-1500:]
        except (OSError, subprocess.TimeoutExpired) as error:
            checks[target] = {'ready': False, 'error': str(error)}
    runtime = ROOT/'.tools/dotnet/dotnet.exe'
    output = ROOT/'integrations/bin/Release/net9.0'
    for name, path in {'dotnet': runtime, 'native_bridge': output/'Vega.Native.dll',
                       'picogk_kernel': output/'picogk.26.2.dll'}.items():
        checks[name] = {'ready': path.is_file(), 'path': str(path)}
    ready = all(check['ready'] for check in checks.values())
    return {'status': 'ok' if ready else 'degraded', 'ready': ready,
            'scope': 'coupled_computational_engineering_model', 'version': '0.30.0',
            'checks': checks, 'repair_command': 'powershell -File setup.ps1',
            'scope_note': 'Dependency readiness only; physical validation and mesh acceptance are separate.'}


if __name__ == '__main__':
    report = readiness()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['ready'] else 1)
