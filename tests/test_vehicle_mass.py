import math
import unittest
from dataclasses import replace
from vega.vehicle_mass import capped_tank_volume_mm3, inverse_tank_growth, estimate_vehicle_mass
from vega.rocket import RocketBrief, design


class VehicleMassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief=RocketBrief(propellant_model='assumed',jacket_pattern='none')
        cls.study=design(cls.brief);cls.candidate=cls.study['candidates'][0]

    def test_tank_volume_matches_independent_outer_minus_cavity(self):
        expected=math.pi*12**2*50-math.pi*10**2*46
        self.assertAlmostEqual(capped_tank_volume_mm3(10,2,50),expected)
        for values in [(10,2,4),(math.nan,2,50)]:
            with self.assertRaises(ValueError):capped_tank_volume_mm3(*values)

    def test_inverse_solution_closes_independent_rocket_equation(self):
        dv,ve,fixed,k=1200,3000,100,.05
        result=inverse_tank_growth(dv,ve,fixed,k);p=result['propellant_mass_kg']
        self.assertAlmostEqual(ve*math.log((fixed+k*p+p)/(fixed+k*p)),dv)
        self.assertLess(abs(result['delta_v_residual_m_s']),1e-8)
        self.assertGreater(p,inverse_tank_growth(dv,ve,fixed,0)['propellant_mass_kg'])

    def test_structural_feedback_can_preclude_any_finite_solution(self):
        result=inverse_tank_growth(3000*math.log(3),3000,100,.6)
        self.assertEqual(result['status'],'no_finite_single_stage_solution')
        self.assertIsNone(result['propellant_mass_kg'])

    def test_geometry_mass_closes_and_density_drives_mass(self):
        baseline=self.candidate['vehicle_mass_model']
        self.assertAlmostEqual(baseline['modeled_material_mass_kg'],sum(r['mass_kg'] for r in baseline['components']))
        heavier=estimate_vehicle_mass(replace(self.brief,assembly_material_density_kg_m3=5400),self.candidate)
        structural=sum(r['mass_kg'] for r in baseline['components'] if r['assumed_density_kg_m3']==2700 and r['id'] not in ('fuel_tank','oxidizer_tank'))
        self.assertAlmostEqual(heavier['modeled_material_mass_kg']-baseline['modeled_material_mass_kg'],structural)

    def test_underbudgeted_dry_mass_and_diameter_fail(self):
        checks=self.candidate['vehicle_mass_model']['checks']
        self.assertFalse(checks['selected_dry_mass_covers_estimate'])
        self.assertFalse(checks['vehicle_reference_diameter_contains_assembly_envelope'])

    def test_component_mass_and_envelope_drive_both_flight_and_mission(self):
        b=replace(self.brief,vehicle_mass_mode='component_estimate')
        candidate=design(b)['candidates'][0];mass=candidate['vehicle_mass_model']
        mission=candidate['vehicle_screen'];flight=candidate['flight_screen']
        self.assertAlmostEqual(mission['vehicle']['dry_mass_excluding_payload_kg'],mass['estimated_dry_mass_kg'])
        self.assertAlmostEqual(flight['launch_mass_kg'],mission['vehicle']['budget_initial_mass_kg'])
        self.assertAlmostEqual(mission['vehicle']['reference_area_m2'],math.pi*(mass['selected_reference_diameter_m']/2)**2)
        self.assertTrue(all(mass['checks'].values()))
        self.assertLess(mission['budget']['available_ideal_delta_v_m_s'],self.candidate['vehicle_screen']['budget']['available_ideal_delta_v_m_s'])

    def test_input_domain_and_declared_delta_v_allowance(self):
        for fields in ({'vehicle_mass_mode':'magic'},{'core_material_density_kg_m3':-1},{'vehicle_mass_margin_fraction':2}):
            with self.assertRaises(ValueError):RocketBrief.parse(fields)
        b=replace(self.brief,mission_delta_v_allowance_m_s=500)
        result=design(b)['candidates'][0]['vehicle_screen']
        self.assertAlmostEqual(result['budget']['remaining_speed_gap_m_s']-self.candidate['vehicle_screen']['budget']['remaining_speed_gap_m_s'],500)
