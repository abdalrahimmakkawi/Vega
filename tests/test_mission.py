"""Behavioral checks for mission bookkeeping and honest model boundaries."""
import math
import unittest
from dataclasses import replace
from vega.rocket import RocketBrief, solve, design
from vega.combined_cycle import atmosphere, screen_combined_cycle
from vega.flight import screen_flight


class MissionTests(unittest.TestCase):
    def setUp(self):
        self.brief = RocketBrief(propellant_model='assumed')
        self.performance = solve(self.brief)

    def screen(self, **changes):
        b = replace(self.brief, **changes)
        return screen_combined_cycle(b, self.performance)

    def test_small_engine_cannot_pass_orbital_mission(self):
        result = self.screen()
        self.assertFalse(result['screen_pass'])
        self.assertEqual(result['status'], 'failed')
        self.assertLess(result['budget']['velocity_margin_m_s'], -5000)
        self.assertIsNone(result['checks']['mode_transition'])
        self.assertIsNone(result['transition']['net_thrust_n'])

    def test_payload_reduces_delta_v_and_is_in_shared_mass_budget(self):
        light = self.screen(payload_mass_kg=0)
        heavy = self.screen(payload_mass_kg=1000)
        self.assertLess(heavy['budget']['available_ideal_delta_v_m_s'],
                        light['budget']['available_ideal_delta_v_m_s'])
        vehicle = heavy['vehicle']
        flight = screen_flight(self.brief, self.performance, suggest=False)
        self.assertAlmostEqual(vehicle['budget_initial_mass_kg'], flight['launch_mass_kg'])
        self.assertAlmostEqual(heavy['budget']['available_ideal_delta_v_m_s'], flight['vacuum_ideal_delta_v_m_s'])
        self.assertEqual(flight['burnout_altitude_m'], self.brief.launch_altitude_m)
        self.assertEqual(flight['burnout_speed_m_s'], 0)

    def test_mass_closure_and_independent_delta_v(self):
        r = self.screen()
        v, budget = r['vehicle'], r['budget']
        self.assertAlmostEqual(v['budget_initial_mass_kg']-v['budget_final_mass_kg'],
                               self.performance['mass_flow_kg_s']*self.brief.burn_duration_s)
        expected = budget['vacuum_effective_exhaust_velocity_m_s'] * math.log(
            v['budget_initial_mass_kg']/v['budget_final_mass_kg'])
        self.assertAlmostEqual(expected, budget['available_ideal_delta_v_m_s'])

    def test_positive_speed_margin_never_claims_feasibility(self):
        r = self.screen(transition_mach=30)  # Internal fixture, outside public input domain.
        self.assertGreater(r['budget']['velocity_margin_m_s'], 0)
        self.assertIsNone(r['screen_pass'])
        self.assertEqual(r['status'], 'incomplete')

    def test_families_have_distinct_dependencies(self):
        for family in ('rocket_only','rbcc','tbcc','ejector_rocket'):
            r = self.screen(propulsion_family=family)
            ids = {s['id'] for s in r['systems']}
            self.assertEqual('turbine' in ids, family == 'tbcc')
            self.assertEqual('ejector' in ids, family in ('rbcc','ejector_rocket'))
            self.assertEqual(r['transition'] is None, family == 'rocket_only')
            for s in r['systems']:
                self.assertTrue(set(s['depends_on']).issubset(ids))
        self.assertIn('separate orbital rocket', self.screen(propulsion_family='tbcc')['family_name'])

    def test_inlet_area_changes_capture_not_invented_thrust(self):
        a, b = self.screen(inlet_capture_area_m2=1), self.screen(inlet_capture_area_m2=2)
        self.assertAlmostEqual(2*a['transition']['ideal_capture_mass_flow_kg_s'],
                               b['transition']['ideal_capture_mass_flow_kg_s'])
        self.assertEqual(a['budget'], b['budget'])
        self.assertIsNone(b['transition']['net_thrust_n'])

    def test_atmosphere_and_input_domain(self):
        sea, high = atmosphere(0), atmosphere(25000)
        self.assertAlmostEqual(sea['density_kg_m3'], 1.226, delta=.01)
        self.assertAlmostEqual(high['speed_of_sound_m_s'], 295, delta=2)
        self.assertLess(high['density_kg_m3'], sea['density_kg_m3'])
        for brief in ({'transition_altitude_m':33000}, {'transition_mach':float('nan')},
                      {'launch_altitude_m':26000}, {'propulsion_family':'unknown'}):
            with self.assertRaises(ValueError): RocketBrief.parse(brief)
        for altitude in (-1,33000,float('nan')):
            with self.assertRaises(ValueError): atmosphere(altitude)

    def test_engine_geometry_is_not_a_decorative_vehicle_shell(self):
        r = design(self.brief)
        c = r['candidates'][0]
        self.assertNotIn('vehicle', c['geometry'])
        self.assertNotIn('lifting_body', [p['id'] for p in c['components']])
        self.assertEqual(r['execution']['airframe_envelope'], 'not_modeled')
        self.assertEqual(c['vehicle_screen']['vehicle']['rocket_propellant_mass_kg'],
                         c['performance']['mass_flow_kg_s']*self.brief.burn_duration_s)


if __name__ == '__main__':
    unittest.main()
