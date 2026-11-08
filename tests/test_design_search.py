import unittest
from dataclasses import asdict, replace
from vega.rocket import RocketBrief
from vega.design_search import explore,proposals,VARIABLES,signature,distance


class DesignSearchTests(unittest.TestCase):
    def test_search_preserves_performance_requirements_and_generates_distinct_geometry(self):
        brief=RocketBrief(search_evaluations=32,search_mesh_limit=5,propellant_model='assumed',propulsion_family='rocket_only',jacket_pattern='none',cooling_passages=0)
        original=asdict(brief)
        for _,proposal in proposals(brief):
            for key,value in asdict(proposal).items():
                if key not in VARIABLES:self.assertEqual(value,original[key],key)
        chosen,report=explore(brief)
        self.assertEqual(report['evaluated'],32)
        self.assertEqual(len(chosen),5)
        self.assertEqual(len({signature(p['run']) for p in chosen}),5)
        self.assertTrue(all(distance(a['run'],b['run'])>0 for i,a in enumerate(chosen) for b in chosen[i+1:]))
        self.assertEqual(len(report['unmeshed_candidates']),27)
        # Geometry is recomputed, not merely given different names.
        geometries=[p['run']['candidates'][0]['geometry'] for p in chosen]
        self.assertGreater(len({str(g['profile_mm']) for g in geometries}),1)
        self.assertGreater(len({str(g['systems']['tanks']) for g in geometries}),1)

    def test_early_preview_does_not_override_final_rank(self):
        from vega.rocket import design
        brief=RocketBrief(search_evaluations=8,search_mesh_limit=2,
                          propellant_model='assumed',propulsion_family='rocket_only',
                          jacket_pattern='none',cooling_passages=0)
        previews=[]
        def evaluate(proposal):
            run=design(proposal,screening=True)
            candidate=run['candidates'][0]
            for checks in (candidate['engineering']['checks'],
                           candidate['geometry_audit']['checks'],
                           candidate['manufacturing']['checks']):
                for key in checks:checks[key]=True
            candidate['engineering']['preliminary_score_lower_is_better']=(
                1000 if not previews else 0)
            return run
        def preview(item):
            previews.append(item['geometry_sha256'])
            return True
        chosen,_=explore(brief,evaluator=evaluate,on_first=preview)
        self.assertNotEqual(chosen[0]['geometry_sha256'],previews[0])

    def test_budget_preserves_proposal_prefix_and_validates_counts(self):
        brief=RocketBrief(search_evaluations=8)
        first=[asdict(p) for _,p in proposals(brief)]
        extended=[asdict(p) for _,p in proposals(replace(brief,search_evaluations=16))][:8]
        for a,b in zip(first,extended):
            a.pop('search_evaluations');b.pop('search_evaluations')
            self.assertEqual(a,b)
        for key in ('search_evaluations','search_mesh_limit'):
            with self.assertRaises(ValueError):RocketBrief.parse({key:8.5})

class AttemptPersistenceTests(unittest.TestCase):
    def test_every_proposal_is_recorded_before_worker_and_failure_is_isolated(self):
        from vega.rocket import design
        brief=RocketBrief(search_evaluations=8,search_mesh_limit=2,
            propellant_model='assumed',propulsion_family='rocket_only',
            jacket_pattern='none',cooling_passages=0)
        records=[]
        def evaluate(proposal):
            self.assertEqual(records[-1]['status'],'running')
            self.assertEqual(records[-1]['requirements'],asdict(proposal))
            if records[-1]['proposal_index']==0:raise RuntimeError('worker crash')
            return design(proposal,screening=True)
        selected,report=explore(brief,evaluator=evaluate,on_attempt=records.append)
        self.assertEqual(len(report['attempts']),8)
        self.assertEqual(report['attempts'][0]['status'],'rejected')
        self.assertEqual(len(records),16)
        self.assertTrue(selected)

if __name__=='__main__':unittest.main()
