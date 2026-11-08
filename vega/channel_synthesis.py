"""Bounded deterministic channel-radius synthesis using the coupled evaluator."""
from math import isfinite, pi


def rank(variant):
    score=variant['preliminary_score_lower_is_better']
    if not isfinite(score):raise ValueError('Nonfinite sizing objective')
    return (not variant['checks'].get('operating_point_convergence',False),
            not variant['analytical_screen_pass'],score,variant['channel_radius_mm'])


def size_channels(brief, throat_radius_mm, evaluator):
    """Search each supported channel count, then refine its best radius interval.

    Bounds come from wall, circumferential pitch, minimum ligament and voxel
    resolution. Legacy dimensions remain diagnostic samples if bounds conflict.
    This is a finite design study, not proof of a global optimum.
    """
    winners=[];history=[]
    for count,legacy in ((8,1.5),(12,1.7),(16,1.5)):
        lower=brief.mesh_voxel_mm
        ligament=max(brief.minimum_ligament_mm,2*brief.mesh_voxel_mm)
        pitch=2*pi*(throat_radius_mm+brief.wall_mm/2)/count
        upper=min((brief.wall_mm-max(4.,ligament))/2,(pitch-ligament)/2)
        samples={}
        def sample(radius):
            key=round(radius,10)
            if key not in samples:
                value=evaluator(count,key)
                rank(value)
                samples[key]=value
                history.append({'channel_count':count,'channel_radius_mm':key,
                    'score':value['preliminary_score_lower_is_better'],
                    'screen_pass':value['analytical_screen_pass'],
                    'failed_checks':[k for k,v in value['checks'].items() if v is not True]})
        sample(legacy)
        if upper>lower:
            for index in range(5):sample(lower+(upper-lower)*index/4)
            eligible=sorted(r for r in samples if lower<=r<=upper)
            best=min(eligible,key=lambda r:rank(samples[r]))
            i=eligible.index(best)
            neighbors=eligible[max(0,i-1):i]+eligible[i+1:i+2]
            for neighbor in neighbors:sample((best+neighbor)/2)
        winners.append(min(samples.values(),key=rank))
    return winners,{'method':'bounded channel-count enumeration and radius interval refinement',
        'objective':'existing preliminary stress, hydraulic-loss and thermal score',
        'selection':'converged operating point, passing analytical screens, then minimum score',
        'evaluations':len(history),'samples':history,
        'limits':'Finite local refinement of supported parallel-channel geometry; no global optimum or physical validation claimed.'}
