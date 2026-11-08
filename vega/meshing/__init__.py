"""Vega mesh backend: CAD surfaces, hybrid flow volumes and solver evidence.

The engineering geometry is expressed in mm. Solver writers explicitly convert
to SI for OpenFOAM and retain mm/N/MPa for CalculiX and MAPDL.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT/'packages/vega-geometry', ROOT/'.tools/python', ROOT/'.tools/meshing'):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

VERSION = '0.29.0'
