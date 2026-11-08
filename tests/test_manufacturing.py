import json
import unittest
from dataclasses import replace
from vega.manufacturing import catalog, constrain, screen
from vega.rocket import RocketBrief, design


class ManufacturingTests(unittest.TestCase):
    def test_catalog_is_small_and_returns_independent_data(self):
        a=catalog()
        self.assertGreaterEqual(len(a['materials']),50)
        self.assertLess(len(json.dumps(a)),40000)
        self.assertEqual(len(a['materials']),len({m['id'] for m in a['materials']}))
        a['materials'].clear()
        self.assertGreater(len(catalog()['materials']),0)

    def test_constraints_drive_actual_geometry(self):
        b=RocketBrief(propellant_model='assumed',propulsion_family='rocket_only',
                      cooling_passages=0,jacket_pattern='none',wall_mm=3,
                      print_min_wall_mm=5,print_min_ligament_mm=3)
        run=design(b)
        c=run['candidates'][0]
        self.assertEqual(c['geometry']['wall_mm'],5)
        self.assertEqual(c['geometry']['minimum_ligament_mm'],3)
        self.assertEqual(run['requirements']['wall_mm'],5)
        self.assertTrue(c['manufacturing']['checks']['nominal_wall'])
        self.assertFalse(c['manufacturing']['print_ready'])

    def test_unknown_envelope_is_not_a_pass_and_small_bed_fails(self):
        c={'dimensions':{'length_mm':400,'diameter_mm':150}}
        b=RocketBrief()
        self.assertNotIn('conservative_build_envelope',screen(b,c)['checks'])
        b=replace(b,print_build_x_mm=100,print_build_y_mm=100,print_build_z_mm=100)
        self.assertFalse(screen(b,c)['checks']['conservative_build_envelope'])
        self.assertEqual(screen(b,c)['status'],'failed_constraints')

    def test_bad_identifiers_rejected(self):
        for key in ('material_id','print_process','test_purpose'):
            with self.assertRaises(ValueError):RocketBrief.parse({key:'invalid'})

    def test_named_material_cannot_silently_inherit_properties(self):
        with self.assertRaisesRegex(ValueError,'explicit engineering properties'):
            RocketBrief.parse({'material_id':'pla'})

    def test_polymer_conductivity_can_be_entered(self):
        self.assertEqual(RocketBrief.parse({'wall_conductivity_w_m_k':.2}).wall_conductivity_w_m_k,.2)
