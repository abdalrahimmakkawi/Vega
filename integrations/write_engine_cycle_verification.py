"""Write a small, solver-bound verification record without native geometry export."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vega.rocket import RocketBrief, solve
from vega.combined_cycle import screen_combined_cycle


brief = RocketBrief()
rocket = solve(brief)
screen = screen_combined_cycle(brief, rocket)
cycle = screen['engine_cycle']
record = {'brief': {'propulsion_family': brief.propulsion_family, 'air_fuel_ratio': brief.air_fuel_ratio,
                    'air_combustion_efficiency': brief.air_combustion_efficiency},
          'engine_cycle': cycle, 'status': cycle['status']}
(ROOT / 'docs/ENGINE_CYCLE_030_RESULT.json').write_text(json.dumps(record, indent=2))
print(ROOT / 'docs/ENGINE_CYCLE_030_RESULT.json')
print(cycle['status'], cycle['net_thrust_n'])
