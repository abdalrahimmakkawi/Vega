import unittest
from vega.rocket import RocketBrief, solve
from vega.combined_cycle import screen_combined_cycle


class EngineCycleTests(unittest.TestCase):
    def test_default_combined_cycle_closes_and_reports_net_thrust(self):
        brief = RocketBrief()
        result = screen_combined_cycle(brief, solve(brief))
        cycle = result['engine_cycle']
        self.assertEqual(cycle['status'], 'screened_closed')
        self.assertGreater(cycle['net_thrust_n'], 0)
        self.assertTrue(all(cycle['checks'].values()))
        self.assertLess(abs(cycle['residuals']['energy_w']), 1e-3)
        station = cycle['stations']['common_nozzle_exit']
        self.assertGreater(station['pressure_pa'], 0)
        self.assertLess(station['pressure_pa'], cycle['stations']['combustor_exit']['total_pressure_pa'])

    def test_air_fuel_ratio_changes_cycle_state(self):
        low = RocketBrief(air_fuel_ratio=20)
        high = RocketBrief(air_fuel_ratio=60)
        low_cycle = screen_combined_cycle(low, solve(low))['engine_cycle']
        high_cycle = screen_combined_cycle(high, solve(high))['engine_cycle']
        self.assertGreater(low_cycle['streams']['air_fuel_kg_s'], high_cycle['streams']['air_fuel_kg_s'])
        self.assertGreater(low_cycle['heat_release_w'], high_cycle['heat_release_w'])
        self.assertNotEqual(low_cycle['net_thrust_n'], high_cycle['net_thrust_n'])


if __name__ == '__main__':
    unittest.main()
