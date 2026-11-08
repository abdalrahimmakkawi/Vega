"""Label the two actual hybrid cell classes for independent viewer toggles."""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vega.meshing.study import artifact_path,digest,refresh_archive


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    args=parser.parse_args()
    path=ROOT/'data'/(args.run_id+'.json')
    run=json.loads(path.read_text())
    folder=ROOT/'data/analysis'/run['id']
    report=run['mesh_study']
    for name in ('scene.json','airpath-scene.json'):
        if name not in report['files']:continue
        scene=json.loads(artifact_path(run,ROOT,name).read_text())
        for body in scene['bodies']:
            body['group']={'fluid_core':'fluid_core','wall_layers':'wall_layers'}[body['component_id']]
        (folder/name).write_text(json.dumps(scene,separators=(',',':')))
        report['files'][name]=digest(folder/name)
    refresh_archive(folder,report)
    temporary=path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(run,indent=2))
    temporary.replace(path)
    print('Refreshed bound hybrid scenes for',run['id'])


if __name__=='__main__':main()
