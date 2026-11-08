"""Write an evidence snapshot from an existing bound solver study."""
from pathlib import Path
import argparse
import json
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vega.meshing.study import artifact_path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    args=parser.parse_args()
    run=json.loads((ROOT/'data'/(args.run_id+'.json')).read_text())
    archive=artifact_path(run,ROOT,'engineering-mesh.zip')
    with zipfile.ZipFile(archive) as bundle:
        corrupt=bundle.testzip()
        if corrupt:raise RuntimeError('Corrupt archive member: '+corrupt)
        members=len(bundle.namelist())
    study=run['mesh_study']
    record={'run_id':run['id'],'assembly_recipe_sha256':run['candidates'][0]['assembly']['recipe_sha256'],
        'source':study['source'],'nozzle_mesh':study['selected_mesh'],
        'nozzle_adaptation':study.get('adaptation'),'coarse_cfd':study.get('coarse_cfd'),
        'adaptive_cfd':study.get('adaptive_cfd'),'airpath_mesh':study.get('airpath_mesh'),
        'airpath_cfd':study.get('airpath_cfd'),'fea':study.get('fea'),
        'archive':{'members':members,'crc':'passed','sha256':study['files']['engineering-mesh.zip']},
        'runtime':study['runtime']}
    out=ROOT/'docs'/('MESH_'+study['version'].split('.')[0]+study['version'].split('.')[1]+'_VERIFICATION.json')
    out.write_text(json.dumps(record,indent=2))
    print(out)


if __name__=='__main__':main()
