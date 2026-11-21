import unittest
from copy import deepcopy
from vega.component_network import component_model, check_connectivity, assessment


class ComponentNetworkTests(unittest.TestCase):
    def setUp(self):
        self.model = component_model({'components': [
            {'id': 'precooler'}, {'id': 'lp-compressor'}, {'id': 'cold-air-supply'},
            {'id': 'lh2-reservoir'}]})

    def test_intent_is_connected_but_not_ready_or_geometry_proof(self):
        result = check_connectivity(self.model)
        self.assertTrue(result['topology_valid'], result['errors'])
        self.assertFalse(result['ready_for_sizing'])
        self.assertFalse(result['geometry_verified'])
        self.assertIn('precooler:pressure_loss_model', result['missing_data'])
        self.assertIn('lp-compressor:performance_map', result['missing_data'])
        self.assertIn('hp-compressor:geometry:hp-compressor', result['missing_data'])
        self.assertEqual(len(self.model['circuits']), 4)
        for identity in ('cold-air-supply', 'lh2-reservoir'):
            self.assertFalse(any(p['component'] == identity for p in self.model['ports']))

    def test_connection_failures(self):
        for mutation, expected in [
            (lambda m: m['connections'].pop(1), 'Required port'),
            (lambda m: m['connections'].append(deepcopy(m['connections'][0])), 'Duplicate edge'),
            (lambda m: m['connections'][0].update(target='missing'), 'Dangling endpoint'),
            (lambda m: m['connections'][0].update(target='bypass-fan.bypass-air.in'), 'Incompatible connection'),
            (lambda m: m['ports'][1].update(fluid='water'), 'fluid mismatch'),
            (lambda m: m['passages'].pop(0), 'Disconnected circuit'),
            (lambda m: m['ports'][1].update(diameter_mm=-1), 'Invalid diameter'),
            (lambda m: m['ports'][1].update(position_mm=[0, float('nan'), 0]), 'Invalid position'),
            (lambda m: m['circuits'][0].update(source='missing'), 'Invalid circuit boundary'),
        ]:
            with self.subTest(expected=expected):
                model = deepcopy(self.model); mutation(model)
                result = check_connectivity(model)
                self.assertFalse(result['topology_valid'])
                self.assertTrue(any(expected in e for e in result['errors']), result['errors'])

    def test_heat_exchanger_sides_do_not_mix(self):
        model = deepcopy(self.model)
        main = next(p for p in model['passages'] if p['source'] == 'precooler.main-air.in')
        main['target'] = 'precooler.exchanger-cooling.out'
        self.assertFalse(check_connectivity(model)['topology_valid'])

    def test_interface_mismatch_and_duplicate_identity(self):
        self.model['ports'][0]['diameter_mm'] = 2
        self.model['ports'][1]['diameter_mm'] = 3
        self.assertTrue(any('Incompatible diameter' in e for e in check_connectivity(self.model)['errors']))
        self.model['ports'].append(deepcopy(self.model['ports'][0]))
        with self.assertRaises(ValueError):
            check_connectivity(self.model)

    def test_disconnected_cycle_is_rejected(self):
        model = deepcopy(self.model)
        connections = model['connections']
        # Bypass one component and connect it to itself: degree alone must not pass.
        connections[0]['target'] = connections[1]['target']
        connections[1]['target'] = 'precooler.main-air.in'
        result = check_connectivity(model)
        self.assertTrue(any('Disconnected circuit: main-air' == e for e in result['errors']))

    def test_assessment_does_not_mutate_source(self):
        report = {'recipe': {'components': [{'id': 'precooler'}]}, 'bodies': [{'component_id': 'half-a'}]}
        original = deepcopy(report)
        result = assessment(report)
        self.assertEqual(report, original)
        self.assertEqual(len(result['source_recipe_sha256']), 64)
        self.assertNotIn('core-jacket:geometry:half-a', result['validation']['missing_data'])


if __name__ == '__main__':
    unittest.main()
