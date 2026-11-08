"""Run the generated frame deck when a licensed MAPDL installation is supplied.

Usage: python integrations/run_ansys.py data/analysis/RUN_ID/fea/frame.mapdl
Set VEGA_MAPDL_EXECUTABLE to the authorized local MAPDL solver executable.
Client installation alone does not satisfy this requirement.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.tools/ansys'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('deck',type=Path);args=parser.parse_args()
    executable=os.environ.get('VEGA_MAPDL_EXECUTABLE')
    if not executable or not Path(executable).is_file():
        parser.error('Set VEGA_MAPDL_EXECUTABLE to a licensed installed MAPDL executable; the PyMAPDL client is not the solver.')
    deck=args.deck.resolve()
    if not deck.is_file() or deck.suffix!='.mapdl':parser.error('Expected an existing generated .mapdl deck')
    from ansys.mapdl.core import launch_mapdl
    solver=launch_mapdl(exec_file=executable,run_location=str(deck.parent/'ansys'),
                        override=True,nproc=2,mode='grpc',start_timeout=120)
    try:
        transcript=solver.input(str(deck))
        (deck.parent/'ansys-output.txt').write_text(str(transcript),encoding='utf-8')
        result=solver.result
        _,u=result.nodal_displacement(-1)
        import numpy as np
        if not np.isfinite(u).all():raise RuntimeError('ANSYS returned nonfinite displacements')
        report={'solver':'MAPDL','status':'computed','maximum_displacement_mm':float(np.linalg.norm(u,axis=1).max()),
                'scope':'Selected axial-bar frame; final transverse load case. No whole-vehicle qualification.'}
        (deck.parent/'ansys-result.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
    finally:solver.exit()


if __name__=='__main__':main()
