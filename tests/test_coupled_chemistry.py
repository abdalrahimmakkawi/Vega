import unittest
from copy import deepcopy
from math import sqrt

from vega.rocket import RocketBrief, design, chamber_properties
from vega.propulsion_model import apply_operating_load_screen


class CoupledChemistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief = RocketBrief(propulsion_family='rocket_only',jacket_pattern='none',channel_variant=8)
        cls.study = design(cls.brief)
        cls.candidate = cls.study['candidates'][0]

    def test_actual_cea_state_is_evaluated_at_solved_pressure_and_ratio(self):
        op = self.candidate['engineering']['operating_point']
        state = op['variables']
        pressure = state['chamber_pressure']['value']
        fuel = state['fuel_flow']['value']; oxidizer = state['oxidizer_flow']['value']
        chemistry = chamber_properties(self.brief,pressure,oxidizer/fuel)
        self.assertEqual(chemistry,op['converged_chemistry'])
        self.assertGreater(op['chemistry_evaluations'],1)
        g,t,r = (chemistry[k] for k in ('gamma','chamber_temperature_k','gas_constant_j_kg_k'))
        throat = self.candidate['performance']['throat_area_m2']
        predicted = throat*pressure/sqrt(t)*sqrt(g/r)*(2/(g+1))**((g+1)/(2*(g-1)))
        self.assertAlmostEqual(fuel+oxidizer,predicted,places=8)

    def test_operating_load_drives_stress_and_candidate_score(self):
        eng = self.candidate['engineering']
        stress = eng['structural_screen']
        pressure = eng['operating_point']['variables']['chamber_pressure']['value']
        self.assertAlmostEqual(stress['governing_pressure_pa'],max(pressure,self.brief.chamber_pressure_bar*1e5))
        self.assertGreater(stress['shell_hoop_mpa'],stress['design_point_shell_hoop_mpa'])
        modified = deepcopy(eng)
        operating = deepcopy(eng['operating_point'])
        operating['variables']['chamber_pressure']['value'] *= 10
        apply_operating_load_screen(self.brief,modified,operating,self.candidate['geometry']['profile_mm'][0][1])
        self.assertGreater(modified['preliminary_score_lower_is_better'],eng['preliminary_score_lower_is_better'])
        self.assertGreater(modified['structural_screen']['utilization'],stress['utilization'])


if __name__ == '__main__':
    unittest.main()

