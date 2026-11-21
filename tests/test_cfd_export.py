import json
import tempfile
import unittest
from pathlib import Path
from vega.cfd_export import export_case


class CfdExportTests(unittest.TestCase):
    def test_export_is_explicitly_gated_until_fluid_domains_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            report = {'bodies': [{'component_id': 'half-a'}], 'base_run': 'run'}
            network = {'source_recipe_sha256': 'a' * 64,
                       'model': {'circuits': [{'id': 'main-air', 'requirement': 'main'}], 'ports': []},
                       'validation': {'topology_valid': True, 'geometry_verified': False, 'missing_data': ['main-air:boundary_conditions']},
                       'concept_requirement': {'net_thrust_target_n': 11000, 'operating_point': {'ambient_temperature_k': 288.15, 'ambient_pressure_pa': 101325}}}
            manifest = export_case(folder, report, network)
            self.assertFalse(manifest['solver_ready'])
            self.assertEqual(manifest['status'], 'case-definition-only')
            self.assertEqual(manifest['target']['net_thrust_target_n'], 11000)
            self.assertTrue((folder/'openfoam-case.zip').is_file())
            self.assertEqual(json.loads((folder/'fluent-case.json').read_text())['units']['geometry'], 'mm')


if __name__ == '__main__':
    unittest.main()
