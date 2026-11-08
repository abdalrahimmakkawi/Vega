"""Attach a verified five-stage CFD case to an existing Vega study."""
from pathlib import Path
import argparse
import json
import shutil
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vega.meshing.airpath import build_airpath
from vega.meshing.hybrid import write_msh, inspection_scene
from vega.meshing.study import artifact_path, digest, refresh_archive
from vega.computational_model import build_model_trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    parser.add_argument('case_dir', type=Path)
    args = parser.parse_args()
    path = ROOT/'data'/(args.run_id+'.json')
    run = json.loads(path.read_text())
    artifact_path(run, ROOT, 'selected.msh')
    case = args.case_dir.resolve()
    if not case.is_relative_to(ROOT) or not (case/'result.json').is_file():
        raise ValueError('Case must be a completed workspace CFD run')
    result = json.loads((case/'result.json').read_text())
    if result['checkMesh'] != 'passed' or 'Mesh OK.' not in (case/'checkMesh.log').read_text():
        raise ValueError('The CFD case did not pass OpenFOAM mesh checks')
    assembly = run['candidates'][0]['assembly']
    mesh, stations = build_airpath(assembly,run['requirements'].get('mesh_surface_edge_mm',12))
    folder = ROOT/'data/analysis'/run['id']
    write_msh(mesh,folder/'airpath.msh')
    if digest(folder/'airpath.msh') != digest(case/'flow.msh'):
        raise ValueError('Saved CFD solution was computed on a different volume mesh')
    if (folder/'airpath').exists():
        raise ValueError('Airpath case already attached; refusing to replace it')
    shutil.copytree(case,folder/'airpath',ignore=shutil.ignore_patterns('.run-*','full.msh'))
    (folder/'airpath-scene.json').write_text(json.dumps(inspection_scene(mesh),separators=(',',':')))
    np.savez_compressed(folder/'airpath-volume.npz',nodes_mm=mesh.nodes,
        prisms=mesh.cells[6],hexahedra=mesh.cells[5],axial_levels_mm=mesh.axial_levels)
    report=run['mesh_study']
    report['airpath_mesh']=mesh.summary
    report['airpath_cfd']=result
    input_path=folder/'inputs.json';input_record=json.loads(input_path.read_text())
    input_record['duct_stages']=assembly['sections']
    input_path.write_text(json.dumps(input_record,indent=2))
    report['input_sha256']=digest(input_path)
    for name in ('airpath.msh','airpath-scene.json','airpath-volume.npz'):
        report['files'][name]=digest(folder/name)
    refresh_archive(folder,report)
    run['execution']['five_stage_airpath']='converged' if result['converged'] else 'not_converged'
    run['computational_model']=build_model_trace(run)
    temporary=path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(run,indent=2))
    temporary.replace(path)
    print(json.dumps({'run_id':run['id'],'cells':mesh.summary['cells'],
        'solver_converged':result['converged'],'pressure_drop_pa':result['pressure_drop_pa']},indent=2))


if __name__=='__main__':main()
