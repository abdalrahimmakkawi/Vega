import unittest
from vega.rocket import RocketBrief, design
from vega.channel_synthesis import size_channels
from vega.propulsion_model import predict_fixed_hardware, fixed_nozzle_performance


class ChannelSynthesisTests(unittest.TestCase):
    def test_radius_is_solved_from_objective_and_keeps_legacy_comparison(self):
        brief=RocketBrief(propellant_model='assumed')
        def objective(target):
            def evaluate(count,radius):
                return {'channel_count':count,'channel_radius_mm':radius,
                    'checks':{'operating_point_convergence':True},
                    'analytical_screen_pass':True,
                    'preliminary_score_lower_is_better':(radius-target)**2}
            return evaluate
        small,record=size_channels(brief,12,objective(1.1))
        large,_=size_channels(brief,12,objective(2.6))
        self.assertTrue(all(a['channel_radius_mm']<b['channel_radius_mm'] for a,b in zip(small,large)))
        self.assertLessEqual(record['evaluations'],24)
        for count,radius in ((8,1.5),(12,1.7),(16,1.5)):
            self.assertTrue(any(s['channel_count']==count and s['channel_radius_mm']==radius for s in record['samples']))

    def test_full_model_selects_evaluated_radius_and_builds_matching_geometry(self):
        brief=RocketBrief(propellant_model='assumed',propulsion_family='rocket_only',jacket_pattern='none')
        result=design(brief,screening=True)
        candidate=result['candidates'][0];eng=candidate['engineering']
        samples=eng['channel_synthesis']['samples']
        selected=next(s for s in samples if s['channel_count']==eng['channel_count'] and s['channel_radius_mm']==eng['channel_radius_mm'])
        self.assertAlmostEqual(selected['score'],eng['preliminary_score_lower_is_better'])
        self.assertGreater(len(samples),3)
        self.assertAlmostEqual(candidate['geometry']['cooling']['radius_mm'],eng['channel_radius_mm'])
        thermal=eng['thermal']['operating_case']
        operating_fuel=eng['operating_point']['variables']['fuel_flow']['value']
        expected=eng['properties']['fuel_inlet_k']+thermal['heat_load_w']/(operating_fuel*eng['properties']['fuel_cp_j_kg_k'])
        self.assertAlmostEqual(thermal['coolant_outlet_k'],expected)
        self.assertLess(abs(thermal['energy_residual_w']),1e-6)

    def test_supply_changes_thrust_without_changing_nozzle_geometry(self):
        brief=RocketBrief(propellant_model='assumed',propulsion_family='rocket_only',jacket_pattern='none',channel_variant=8)
        candidate=design(brief,screening=True)['candidates'][0]
        performance=candidate['performance'];eng=candidate['engineering']
        predictions=[]
        for supply in (30e5,40e5):
            operating=predict_fixed_hardware(brief,performance,eng,tank_pressure_pa=supply)
            predictions.append(fixed_nozzle_performance(performance,operating,0))
        self.assertGreater(predictions[1]['thrust_n'],predictions[0]['thrust_n'])
        for prediction in predictions:
            self.assertEqual(prediction['throat_area_m2'],performance['throat_area_m2'])
            self.assertEqual(prediction['exit_area_m2'],performance['exit_area_m2'])
            self.assertLess(abs(prediction['mass_balance_residual_kg_s']),1e-8)
            self.assertAlmostEqual(prediction['thrust_n'],prediction['momentum_thrust_n']+prediction['pressure_thrust_n'])
