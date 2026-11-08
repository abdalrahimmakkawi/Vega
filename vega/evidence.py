"""Traceable comparisons against measured engine data, when supplied.

Reference-property and independent-code checks are verification; they are not
called hardware calibration here. Measurements must identify the exact design.
"""
import json
import math
from pathlib import Path

OBSERVATIONS=Path(__file__).resolve().parents[1]/'data'/'evidence'/'observations.json'
OUTPUTS={
    'mass_flow_kg_s':lambda e:e['mass_flow_kg_s']['chamber'],
    'fuel_required_tank_bar':lambda e:e['pressure_bar']['fuel_required'],
    'oxidizer_required_tank_bar':lambda e:e['pressure_bar']['oxidizer_required'],
    'coolant_bulk_outlet_k':lambda e:e['thermal']['estimated_bulk_outlet_k'],
}

def compare(candidate_id,engineering,path=OBSERVATIONS):
    if not path.exists():
        return {'status':'awaiting_measured_data','matched_observations':0,
                'verification':'RocketCEA chemistry, proptools nozzle cross-check, and NASA reference densities are model inputs/checks; they are not hot-fire calibration.'}
    records=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(records,list):raise ValueError('Evidence must be a JSON list')
    comparisons=[]
    for record in records:
        if record.get('candidate_id')!=candidate_id:continue
        if not record.get('source') or not record.get('date'):
            raise ValueError('Matched evidence needs source and date')
        measurements=record.get('measurements',{})
        for key,measurement in measurements.items():
            if key not in OUTPUTS:raise ValueError('Unsupported measurement: '+key)
            if isinstance(measurement,bool) or not isinstance(measurement,(int,float)) or not math.isfinite(measurement):
                raise ValueError('Invalid evidence measurement: '+key)
            prediction=OUTPUTS[key](engineering)
            comparisons.append({'source':record['source'],'date':record['date'],'metric':key,
                                'measured':measurement,'predicted':prediction,'residual':prediction-measurement,
                                'relative_error':abs(prediction-measurement)/max(abs(measurement),1e-9)})
    if not comparisons:
        return {'status':'awaiting_matching_measurements','matched_observations':0}
    return {'status':'comparison_only_no_parameter_fit','matched_observations':len(comparisons),
            'mean_absolute_relative_error':sum(c['relative_error'] for c in comparisons)/len(comparisons),
            'comparisons':comparisons,'note':'Residuals are reported. Model coefficients are not changed without a sufficiently diverse measured dataset and holdout validation.'}
