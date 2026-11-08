"""Isolated, bounded design evaluation worker (no network)."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vega.rocket import RocketBrief
from vega.algorithm import execute
brief=RocketBrief.parse(json.loads(Path(sys.argv[1]).read_text()))
run=execute(brief,screening='--screening' in sys.argv)
Path(sys.argv[2]).write_text(json.dumps(run))
