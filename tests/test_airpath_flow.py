"""Independent equation checks and geometry coupling for conditional flow."""
import unittest
from dataclasses import replace

from vega.airpath_flow import air_viscosity_pa_s, mass_flux, subsonic_station
from vega.rocket import RocketBrief, design


class AirpathFlowTests(unittest.TestCase):
    def test_sutherland_reference_and_station_conservation(self):
        self.assertAlmostEqual(air_viscosity_pa_s(293), 1.796e-5)
        station = subsonic_station('test', .2, 5, 100000, 300, 1.4, 286.9)
        self.assertAlmostEqual(station['mass_flow_kg_s'], 5, places=10)
        self.assertAlmostEqual(station['dynamic_pressure_pa'],
                               station['density_kg_m3'] * station['velocity_m_s']**2 / 2)
        self.assertLess(station['mach'], 1)
        self.assertGreater(station['choking_margin_fraction'], 0)
        critical = mass_flux(1, 100000, 300, 1.4, 286.9)
        with self.assertRaisesRegex(ValueError, 'choked'):
            subsonic_station('too_small', 5 / critical * .9, 5, 100000, 300, 1.4, 286.9)

    def test_pressure_recovery_changes_real_geometry_and_station_state(self):
        brief = RocketBrief(propellant_model='assumed')
        high = design(replace(brief, airpath_pressure_recovery=1))['candidates'][0]['assembly']
        low = design(replace(brief, airpath_pressure_recovery=.7))['candidates'][0]['assembly']
        for assembly in (high, low):
            state = assembly['design_state']
            self.assertTrue(all(state['checks'].values()))
            self.assertLess(state['conditional_airpath']['maximum_relative_mass_residual'], 1e-10)
            self.assertGreater(state['conditional_airpath']['minimum_choking_margin_fraction'], 0)
        self.assertGreater(low['section_design']['mixer_throat_area_m2'],
                           high['section_design']['mixer_throat_area_m2'])
        self.assertNotEqual(low['scene_sha256'], high['scene_sha256'])
        self.assertLess(low['design_state']['conditional_airpath']['assumed_mixed_total_pressure_pa'],
                        high['design_state']['conditional_airpath']['assumed_mixed_total_pressure_pa'])


if __name__ == '__main__':
    unittest.main()
