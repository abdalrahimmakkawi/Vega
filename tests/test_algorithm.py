import unittest
from vega.algorithm import execute

class AlgorithmTests(unittest.TestCase):
    def test_execution_returns_geometry_and_truthful_constraint_evidence(self):
        result=execute({'propellant_model':'assumed','propulsion_family':'rocket_only',
            'cooling_passages':0,'jacket_pattern':'none'},screening=True)
        self.assertTrue(result['candidates'][0]['geometry'])
        self.assertEqual(result['algorithm']['execution_status'],'completed')
        self.assertFalse(result['algorithm']['physically_validated'])
        self.assertEqual(result['algorithm']['requirements_sha256'],result['computational_model']['requirements_sha256'])
        self.assertTrue(result['algorithm']['candidate_outcomes'][0]['checks'])

    def test_invalid_requirements_fail_before_execution(self):
        with self.assertRaises(ValueError):execute({'thrust_n':float('nan')})
