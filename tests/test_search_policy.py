import math
import unittest
from dataclasses import asdict, replace
from vega.design_search import explore, proposals, SearchEvaluationError
from vega.rocket import RocketBrief


def result(brief, identity, score=1, passed=True):
    return {'requirements': asdict(brief), 'candidates': [{
        'geometry': {'identity': identity}, 'assembly': {'recipe_sha256': str(identity)},
        'engineering': {'checks': {'load': passed}, 'preliminary_score_lower_is_better': score},
        'geometry_audit': {'checks': {'closed': True}},
        'manufacturing': {'checks': {'wall': True}},
    }]}


class SearchPolicyTests(unittest.TestCase):
    def test_preview_failure_is_not_misclassified_as_candidate_rejection(self):
        brief = RocketBrief(search_evaluations=8)
        def fail_preview(item):
            raise ValueError('preview storage failed')
        with self.assertRaisesRegex(ValueError, 'preview storage failed') as caught:
            explore(brief, evaluator=lambda b: result(b, 1), on_first=fail_preview)
        self.assertIs(type(caught.exception), ValueError)

    def test_preview_cannot_force_failed_candidate_into_winner(self):
        brief = RocketBrief(search_evaluations=8, search_mesh_limit=2)
        count = iter(range(8))
        selected, report = explore(brief, evaluator=lambda b: result(b, i := next(count), i, i != 0),
                                   on_first=lambda item: True)
        self.assertEqual(selected[0]['proposal_index'], 1)
        self.assertTrue(all(item['feasibility'] == 'screen_pass' for item in selected))

    def test_every_attempt_has_a_ledger_entry(self):
        brief = RocketBrief(search_evaluations=8, search_mesh_limit=2)
        count = iter(range(8))
        def evaluate(b):
            i = next(count)
            if i == 2:
                raise ValueError('unsupported geometry')
            return result(b, 0 if i == 1 else i, math.inf if i == 3 else 1)
        selected, report = explore(brief, evaluator=evaluate)
        self.assertEqual(len(report['attempts']), 8)
        self.assertEqual([r['status'] for r in report['attempts'][:4]],
                         ['evaluated', 'duplicate', 'rejected', 'rejected'])
        self.assertTrue(all(math.isfinite(item['score']) for item in selected))

    def test_unknown_check_is_not_feasible(self):
        brief = RocketBrief(search_evaluations=8, search_mesh_limit=2)
        count = iter(range(8))
        selected, _ = explore(brief, evaluator=lambda b: result(b, next(count), passed=None))
        self.assertTrue(all(item['feasibility'] == 'unresolved' for item in selected))
        self.assertEqual(selected[0]['unresolved_checks'], ['load'])

    def test_all_rejected_search_retains_attempts(self):
        brief = RocketBrief(search_evaluations=8)
        with self.assertRaises(SearchEvaluationError) as caught:
            explore(brief, evaluator=lambda b: result(b, 1, score=math.nan))
        self.assertEqual(caught.exception.report['attempted'], 8)
        self.assertEqual(len(caught.exception.report['rejected']), 8)

    def test_seed_replays_and_preserves_prefix(self):
        brief = RocketBrief(search_evaluations=8, search_seed=123)
        first = [p.chamber_length_mm for _, p in proposals(brief)]
        self.assertEqual(first, [p.chamber_length_mm for _, p in proposals(brief)])
        self.assertEqual(first, [p.chamber_length_mm for _, p in proposals(replace(brief, search_evaluations=16))][:8])
        self.assertNotEqual(first, [p.chamber_length_mm for _, p in proposals(replace(brief, search_seed=124))])
        for invalid in (-1, 2**32, 1.5, True, math.nan):
            with self.assertRaises(ValueError):
                RocketBrief.parse({'search_seed': invalid})


if __name__ == '__main__':
    unittest.main()
