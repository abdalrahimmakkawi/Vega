"""Executable Vega CEM algorithm and command-line entry point.

Run: python -m vega.algorithm requirements.json --output result.json
The supported domain remains the domain of RocketBrief and its models.
"""
from dataclasses import asdict
from pathlib import Path
import argparse
import hashlib
import json
import os
import tempfile
from .rocket import RocketBrief, design
from .computational_model import build_model_trace

VERSION = '1.1'


def execute(requirements, *, screening=False):
    """Validate requirements, execute coupled models, and return evidence.

    A failed engineering constraint is a result, not a runtime failure.
    Numerical execution never promotes missing physical evidence to validation.
    """
    brief = RocketBrief.parse(asdict(requirements) if isinstance(requirements, RocketBrief) else requirements)
    inputs = asdict(brief)
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True, allow_nan=False).encode()).hexdigest()
    run = design(brief, screening=screening)
    trace = build_model_trace(run)
    candidates = []
    for candidate in run['candidates']:
        checks = {}
        for group in ('engineering', 'geometry_audit', 'manufacturing'):
            values = candidate.get(group, {}).get('checks', {})
            if not values:
                checks[group + '.evidence'] = None
            for name, value in values.items():
                checks[group + '.' + name] = value if value is True or value is False else None
        failed = [name for name, value in checks.items() if value is False]
        unresolved = [name for name, value in checks.items() if value is None]
        candidates.append({'candidate_id': candidate['id'],
            'feasibility': 'failed' if failed else 'unresolved' if unresolved else 'model_screen_pass',
            'failed_constraints': failed, 'unresolved_constraints': unresolved,
            'checks': checks, 'evidence_level': 'computational_model_only'})
    run['computational_model'] = trace
    run['algorithm'] = {'name': 'Vega CEM', 'version': VERSION,
        'requirements_sha256': digest, 'mode': 'screening' if screening else 'geometry',
        'execution_status': 'completed', 'candidate_outcomes': candidates,
        'physically_validated': False,
        'scope': 'Existing reduced-order propulsion, feed, cooling, structural, manufacturing and geometry models; see stage assumptions and system completion obligations.'}
    # Reject invalid serialization at the algorithm boundary.
    json.dumps(run, allow_nan=False)
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('requirements', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--screening', action='store_true')
    args = parser.parse_args()
    result = execute(json.loads(args.requirements.read_text(encoding='utf-8')), screening=args.screening)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=args.output.parent, suffix='.tmp')
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(result, stream, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, args.output)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


if __name__ == '__main__':
    main()
