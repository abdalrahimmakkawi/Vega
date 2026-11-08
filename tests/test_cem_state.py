"""Conservation and geometry propagation in the conditional RBCC mixer model."""
import math
import unittest
from dataclasses import replace

from vega.cem_state import ideal_mixer_balance
from vega.combined_cycle import screen_combined_cycle
from vega.rocket import RocketBrief, design, solve


class IdealMixerTests(unittest.TestCase):
    def test_mass_energy_and_critical_area_from_independent_sources(self):
        brief=RocketBrief(propellant_model='assumed')
        rocket=solve(brief)
        inlet=screen_combined_cycle(brief,rocket)['inlet_reference']
        air=inlet['mass_flow_kg_s']
        model=ideal_mixer_balance(air,rocket['mass_flow_kg_s'],inlet,rocket)
        self.assertAlmostEqual(model['mass_flow_kg_s']['mixed'],air+rocket['mass_flow_kg_s'])
        self.assertAlmostEqual(model['energy_residual_w'],0,delta=1e-6)
        self.assertAlmostEqual(model['minimum_ideal_choked_area_m2']*
                               model['critical_mass_flux_at_air_pressure_kg_m2_s'],
                               model['mass_flow_kg_s']['mixed'],places=10)
        temperatures=model['stagnation_temperature_k']
        self.assertLess(temperatures['air'],temperatures['mixed_ideal'])
        self.assertLess(temperatures['mixed_ideal'],temperatures['rocket'])
        self.assertGreater(model['air_total_pressure_after_normal_shock_pa'],0)

    def test_balance_controls_saved_mixer_and_geometry(self):
        brief=RocketBrief(propellant_model='assumed')
        first=design(brief)['candidates'][0]['assembly']
        second=design(replace(brief,transition_mach=2.5))['candidates'][0]['assembly']
        for assembly in (first,second):
            model=assembly['design_state']['ideal_mixer']
            area=assembly['design_state']['area_m2']
            self.assertGreaterEqual(area['mixer_throat'],1.05*model['minimum_ideal_choked_area_m2']-1e-12)
            self.assertGreaterEqual(model['reference_pressure_headroom_fraction'],0)
            self.assertTrue(all(assembly['design_state']['checks'].values()))
            self.assertTrue(all(assembly['checks'].values()))
        self.assertNotEqual(first['recipe_sha256'],second['recipe_sha256'])
        self.assertNotEqual(first['design_state']['ideal_mixer']['stagnation_temperature_k']['mixed_ideal'],
                            second['design_state']['ideal_mixer']['stagnation_temperature_k']['mixed_ideal'])


if __name__=='__main__':
    unittest.main()
