"""Bounded design-space exploration over executable geometry families.

Mission, propellants, thrust, chamber pressure and safety limits remain fixed.
This explores layouts and contours; it does not invent combustion cycles.
"""
from dataclasses import asdict
from hashlib import sha256
from random import Random
import json, math
from .rocket import RocketBrief, design

VARIABLES=('nozzle_contour','tank_layout','chamber_length_mm','chamber_area_ratio',
           'inlet_section','inlet_aspect_ratio','inlet_length_m','mixer_length_dh',
           'combustor_length_dh','combined_throat_ratio','combined_exit_ratio',
           'frame_topology','frame_volume_fraction','channel_variant',
           'nozzle_half_angle_deg','tank_clearance_mm')


class SearchEvaluationError(ValueError):
    """A failed search retains its attempt ledger for job persistence."""
    def __init__(self, message, report):
        super().__init__(message)
        self.report=report


def proposals(brief):
    # Fresh reproducible synthesis from requirements, never a saved mesh.
    seed_inputs={k:v for k,v in asdict(brief).items() if not k.startswith('search_')}
    # Seed zero retains the legacy deterministic stream. Explicit seeds allow
    # independent searches, while budgets never alter a replay's prefix.
    if brief.search_seed:seed_inputs['search_seed']=int(brief.search_seed)
    rng = Random(sha256(json.dumps(seed_inputs, sort_keys=True).encode()).hexdigest())
    for index in range(int(brief.search_evaluations)):
        stretch = rng.uniform(.65, 1.5)
        values=asdict(brief)
        values.update(nozzle_contour=('bell','conical')[index % 2],
            tank_layout=('paired','staggered')[(index // 2) % 2],
            chamber_length_mm=max(40,min(500,brief.chamber_length_mm*stretch)),
            chamber_area_ratio=rng.uniform(2.5,7.5),
            nozzle_half_angle_deg=rng.uniform(8,25),
            tank_clearance_mm=rng.uniform(12,40))
        if brief.propulsion_family!='rocket_only':
            values.update(inlet_section='rectangular' if stretch<1 else 'elliptical',
                inlet_aspect_ratio=max(1,min(10,brief.inlet_aspect_ratio*stretch)),
                inlet_length_m=max(.5,min(20,brief.inlet_length_m*stretch)),
                mixer_length_dh=rng.uniform(1.5,4.5),
                combustor_length_dh=rng.uniform(2,5),
                combined_throat_ratio=rng.uniform(.58,.82),
                combined_exit_ratio=rng.uniform(1.4,3.6),
                frame_topology=('rails','braced','optimized')[index % 3],
                frame_volume_fraction=rng.uniform(.45,.8),
                channel_variant=(8,12,16)[index % 3])
        yield index,RocketBrief.parse(values)


def signature(run):
    c=run['candidates'][0]
    return sha256(json.dumps({'core':c['geometry'],'assembly':c['assembly'].get('recipe_sha256')},sort_keys=True).encode()).hexdigest()


def distance(a,b):
    x,y=a['requirements'],b['requirements']
    categorical=sum(x[k]!=y[k] for k in ('nozzle_contour','tank_layout','inlet_section','frame_topology','channel_variant'))
    dimensional=sum(abs(x[k]-y[k])/max(abs(x[k]),abs(y[k]),1e-9) for k in
        ('chamber_length_mm','chamber_area_ratio','inlet_aspect_ratio','inlet_length_m',
         'mixer_length_dh','combustor_length_dh','combined_throat_ratio','combined_exit_ratio','frame_volume_fraction'))
    return categorical+dimensional


def explore(brief,progress=lambda text:None, *, evaluator=design, on_first=None, compact=False, on_attempt=lambda record:None):
    pool=[];rejected=[];attempts=[];seen=set();first_key=None
    for index,proposal in proposals(brief):
        progress(f'Evaluating geometry candidate {index+1}/{int(brief.search_evaluations)}')
        on_attempt({'proposal_index':index,'status':'running','requirements':asdict(proposal)})
        try:
            run=evaluator(proposal);c=run['candidates'][0];eng=c['engineering']
            score=eng['preliminary_score_lower_is_better']
            if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score):
                raise ValueError('Engineering score must be a finite number')
            key=signature(run)
            if key in seen:
                attempts.append({'proposal_index':index,'status':'duplicate','geometry_sha256':key})
                on_attempt(attempts[-1])
                continue
            seen.add(key)
            failures=[];unresolved=[]
            for prefix,group in (('',eng),('geometry_',c['geometry_audit']),('manufacturing_',c['manufacturing'])):
                checks=group.get('checks',{})
                if not checks:unresolved.append(prefix+'checks_missing')
                for name,passed in checks.items():
                    if passed is False:failures.append(prefix+name)
                    elif passed is not True:unresolved.append(prefix+name)
            feasibility='failed' if failures else 'unresolved' if unresolved else 'screen_pass'
            item={'proposal':proposal,'run':run,'geometry_sha256':key,'failed_checks':failures,
                'unresolved_checks':unresolved,'feasibility':feasibility,
                'score':score,'proposal_index':index}
            attempts.append({'proposal_index':index,'status':'evaluated','geometry_sha256':key,
                'failed_checks':failures,'unresolved_checks':unresolved,'feasibility':feasibility,'score':score})
        except Exception as error:
            rejected.append({'proposal_index':index,'reason':str(error),'requirements':asdict(proposal)})
            attempts.append({'proposal_index':index,'status':'rejected','reason':str(error)})
            on_attempt(attempts[-1])
            continue
        on_attempt(attempts[-1])
        if on_first and first_key is None and on_first(item):first_key=key
        if compact:item['run']={'requirements':run['requirements']};item['needs_rebuild']=True
        pool.append(item)
        del run,c,eng
    if not pool:
        raise SearchEvaluationError('No candidate could be evaluated: '+'; '.join(r['reason'] for r in rejected),
            {'evaluated':0,'attempted':len(attempts),'attempts':attempts,'rejected':rejected,
             'search_seed':int(brief.search_seed)})
    def constraint_rank(p):
        return ({'screen_pass':0,'unresolved':1,'failed':2}[p['feasibility']],len(p['failed_checks']),len(p['unresolved_checks']))
    pool.sort(key=lambda p:(constraint_rank(p),p['score'],p['proposal_index']))
    first=pool[0]
    pool.remove(first);chosen=[first]
    while pool and len(chosen)<int(brief.search_mesh_limit):
        # Honor failure count first; among equally feasible options maximize
        # separation from the already chosen set, then use engineering score.
        best=min(pool,key=lambda p:(constraint_rank(p),
            -min(distance(p['run'],q['run']) for q in chosen),p['score'],p['proposal_index']))
        pool.remove(best);chosen.append(best)
    return chosen,{'evaluated':len(seen),'attempted':len(attempts),'attempts':attempts,
        'search_seed':int(brief.search_seed),'rejected':rejected,'unmeshed_candidates':[
        {'geometry_sha256':p['geometry_sha256'],'failed_checks':p['failed_checks'],'score':p['score'],
         'unresolved_checks':p['unresolved_checks'],'feasibility':p['feasibility'],
         'parameters':{k:asdict(p['proposal'])[k] for k in VARIABLES}} for p in pool],
        'varied_parameters':list(VARIABLES),'fixed_requirements':{k:v for k,v in asdict(brief).items() if k not in VARIABLES},
        'selection_rule':('Early preview does not affect final ranking. ' if first_key else '')+'Passed screens first, unresolved next, failed last; then constraint count, parameter diversity and engineering score. Screen passes are not validation or an optimality guarantee.',
        'scope':'Bounded search across supported nozzle, tank packaging and duct geometry families; no new combustion cycle or topology is inferred.'}
