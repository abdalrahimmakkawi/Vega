import unittest

from vega.rocket import RocketBrief, design


class ComputationalModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study = design(RocketBrief.parse({
            'propellant_model': 'assumed', 'propulsion_family': 'rocket_only',
            'cooling_passages': 0, 'jacket_pattern': 'none', 'thrust_n': 350,
            'burn_duration_s': 1.2,
        }))
        cls.model = cls.study['computational_model']

    def test_stage_graph_is_ordered_and_dependencies_resolve(self):
        stages = self.model['stages']
        positions = {stage['id']: index for index, stage in enumerate(stages)}
        self.assertEqual(len(positions), len(stages))
        for stage in stages:
            for dependency in stage['depends_on']:
                self.assertIn(dependency, positions)
                self.assertLess(positions[dependency], positions[stage['id']])

    def test_equation_chain_reaches_geometry_and_marks_validation_status(self):
        stages = {stage['id']: stage for stage in self.model['stages']}
        self.assertIn('F = mdot Ve + (pe - pa) Ae', stages['nozzle']['equations'])
        self.assertIn('feed_network', stages['thermal']['depends_on'])
        self.assertIn('thermal', stages['geometry']['depends_on'])
        self.assertIn('geometry', stages['assembly']['depends_on'])
        self.assertEqual(stages['mesh_and_export']['status'], 'pending')
        self.assertEqual(self.model['validation']['status'], 'awaiting_measured_data')

    def test_trace_is_bound_to_requirements_and_selected_solution(self):
        self.assertEqual(self.model['candidate_id'], self.study['candidates'][0]['id'])
        self.assertEqual(len(self.model['requirements_sha256']), 64)
        self.assertEqual(len(self.model['model_sha256']), 64)
        nozzle = next(stage for stage in self.model['stages'] if stage['id'] == 'nozzle')
        self.assertAlmostEqual(nozzle['outputs']['mass_flow'][0],
                               self.study['candidates'][0]['performance']['mass_flow_kg_s'])

    def test_numerical_checks_do_not_claim_whole_spacecraft_completion(self):
        assessment=self.model['system_completion']
        self.assertFalse(assessment['complete'])
        self.assertIn('mission_velocity_budget',assessment['failed_requirements'])
        self.assertIn('power_avionics_gnc',{item['id'] for item in assessment['obligations']})


if __name__ == '__main__':
    unittest.main()
