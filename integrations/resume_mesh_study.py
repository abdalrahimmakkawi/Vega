"""Continue checked CFD cases and atomically refresh their run-bound report."""
from pathlib import Path
import argparse
import json
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vega.meshing.solvers import resume_cfd
from vega.meshing.study import artifact_path, digest
from vega.computational_model import build_model_trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    parser.add_argument('--end-time', type=int, default=1600)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{32}', args.run_id):
        parser.error('Expected a run ID')
    path = ROOT / 'data' / (args.run_id + '.json')
    run = json.loads(path.read_text())
    report = run['mesh_study']
    artifact_path(run, ROOT, 'selected.msh')
    folder = ROOT / 'data/analysis' / args.run_id
    stations = run['candidates'][0]['assembly']['sections'][-1]
    # Preserve which preliminary solution actually drove the fixed adaptive mesh.
    report.setdefault('adaptation_source', {
        'time': report['coarse_cfd']['time'],
        'indicator': report['coarse_cfd']['adaptation_indicator'],
        'converged': report['coarse_cfd']['converged'],
    })
    for name in ('coarse', 'adaptive'):
        print('Continuing ' + name, flush=True)
        report[name + '_cfd'] = resume_cfd(folder / name, stations, args.end_time)
    first, second = report['coarse_cfd'], report['adaptive_cfd']
    change = abs(second['pressure_drop_pa'] - first['pressure_drop_pa']) / max(abs(second['pressure_drop_pa']), 1e-12)
    report['adaptation'].update(relative_pressure_drop_change=change,
        converged=bool(first['converged'] and second['converged'] and change < .05))
    report['status'] = 'computed' if report['adaptation']['converged'] else 'computed_not_converged'
    report['files'].pop('engineering-mesh.zip', None)
    (folder / 'report.json').write_text(json.dumps(report, indent=2))
    archive_path = folder / 'engineering-mesh.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(folder.rglob('*')):
            if item.is_file() and item != archive_path and not item.name.startswith('.run-'):
                archive.write(item, item.relative_to(folder).as_posix())
    report['files']['engineering-mesh.zip'] = digest(archive_path)
    run['computational_model'] = build_model_trace(run)
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(run, indent=2))
    temporary.replace(path)
    print(json.dumps({'status': report['status'], 'adaptation': report['adaptation']}, indent=2))


if __name__ == '__main__':
    main()
