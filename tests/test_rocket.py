import unittest
import math
import json
import tempfile
from pathlib import Path
from collections import Counter
from dataclasses import replace
from unittest.mock import patch
from vega.rocket import RocketBrief,solve,design,mesh,area_ratio
from vega.evidence import compare
from vega.flight import screen_flight, G0
from vega.geometry_audit import inspect as inspect_geometry
import server

class RocketTests(unittest.TestCase):
    def test_choked_nozzle_and_force_closure(self):
        b=RocketBrief();c=solve(b)
        self.assertAlmostEqual(area_ratio(c['exit_mach'],c['chemistry']['gamma']),b.expansion_ratio,places=10)
        self.assertLess(c['verification']['relative_error'],1e-6)
        self.assertAlmostEqual(c['momentum_thrust_n']+c['pressure_thrust_n'],b.thrust_n,places=9)
        self.assertGreater(c['exit_mach'],1)
        self.assertAlmostEqual(c['exit_area_m2']/c['throat_area_m2'],b.expansion_ratio)
    def test_thrust_scaling(self):
        a=solve(RocketBrief());b=solve(replace(RocketBrief(),thrust_n=2000))
        self.assertAlmostEqual(b['throat_area_m2'],2*a['throat_area_m2'])
        self.assertAlmostEqual(a['ideal_isp_s'],b['ideal_isp_s'])
    def test_bell_and_conical_contours_share_solved_areas(self):
        bell=design(RocketBrief())['candidates'][0]
        cone=design(RocketBrief(nozzle_contour='conical'))['candidates'][0]
        bp=bell['geometry']['profile_mm'];cp=cone['geometry']['profile_mm']
        self.assertEqual(bp[2][1],cp[2][1])
        self.assertEqual(bp[-1][1],cp[-1][1])
        self.assertLess(bp[-1][0],cp[-1][0])
        self.assertTrue(all(b[0]>a[0] and b[1]>a[1] for a,b in zip(bp[2:],bp[3:])))
        self.assertEqual(bell['performance'],cone['performance'])
        self.assertNotEqual(bell['geometry']['profile_mm'],cone['geometry']['profile_mm'])
    def test_invalid_requirements(self):
        for d in ({'thrust_n':float('nan')},{'gamma':1},{'thrust_n':True},{'unknown_requirement':2},{'architecture':'unsupported'},{'wall_mm':0}):
            with self.subTest(d=d),self.assertRaises(ValueError):RocketBrief.parse(d)
    def test_scene_closed_and_mating(self):
        r=design(RocketBrief());c=r['candidates'][0];m=mesh(c)
        self.assertEqual(len(m['bodies']),3)
        for body in m['bodies']:
            edges=Counter()
            for t in m['triangles'][body['first_triangle']:body['first_triangle']+body['triangle_count']]:
                for a,b in zip(t,t[1:]+t[:1]):edges[tuple(sorted((a,b)))]+=1
            self.assertTrue(all(n==2 for n in edges.values()))
        parts=c['geometry']['components']
        for a,b in zip(parts,parts[1:]):self.assertEqual(a['axial_mm'][1],b['axial_mm'][0])
        self.assertTrue(all(math.isfinite(v) for p in m['vertices'] for v in p))
    def test_legacy_conical_scene_remains_readable(self):
        candidate=design(RocketBrief(nozzle_contour='conical'))['candidates'][0]
        for part in candidate['geometry']['components']:part.pop('profile_indices')
        self.assertEqual(len(mesh(candidate)['bodies']),3)
    def test_native_failure_does_not_complete(self):
        identity='f'*32
        with patch.object(server,'native_export',side_effect=ValueError('native failure')):server.run_job(identity,RocketBrief())
        self.assertEqual(server.JOBS.pop(identity)['status'],'failed')
    def test_backpressure_is_reported(self):
        r=design(replace(RocketBrief(),ambient_pressure_bar=1))
        self.assertTrue(r['warnings']);self.assertEqual(r['execution']['validation'],'not_run')
    def test_jacket_changes_recipe_not_claimed_performance(self):
        a=design(RocketBrief(jacket_pattern='bcc'));b=design(replace(RocketBrief(),jacket_pattern='penrose'))
        self.assertNotEqual(a['candidates'][0]['id'],b['candidates'][0]['id'])
        self.assertEqual(a['candidates'][0]['performance'],b['candidates'][0]['performance'])
        j=a['candidates'][0]['geometry']['jacket'];g=a['candidates'][0]['geometry']
        self.assertGreater(j['inner_radius_mm'],g['profile_mm'][0][1])
        self.assertEqual(a['candidates'][0]['components'][-1]['id'],'jacket')
    def test_jacket_parameter_bounds(self):
        for brief in ({'jacket_pattern':'unknown'},{'beam_radius_mm':3,'cell_size_mm':8}):
            with self.assertRaises(ValueError):RocketBrief.parse(brief)

    def test_connected_fuel_passage_recipe(self):
        candidate=design(RocketBrief(jacket_pattern='none'))['candidates'][0]
        cooling=candidate['geometry']['cooling']
        self.assertEqual(cooling['channel_count'],candidate['engineering']['channel_count'])
        self.assertEqual(len(cooling['paths']),cooling['channel_count']+2)
        ids=[p['id'] for p in candidate['components']]
        self.assertIn('fuel_inlet',ids);self.assertIn('fuel_outlet',ids)
        self.assertIn('fuel_tank',ids);self.assertIn('oxidizer_tank',ids);self.assertIn('injector_head',ids)
        self.assertIn('fuel_return',ids)

    def test_routed_thermal_balance_matches_generated_passage(self):
        candidate=design(RocketBrief())['candidates'][0]
        thermal=candidate['engineering']['thermal']
        route=candidate['geometry']['cooling']['paths'][2]['points']
        length=sum(math.dist(a,b) for a,b in zip(route,route[1:]))/1000
        self.assertAlmostEqual(thermal['route_length_m'],length,places=9)
        self.assertAlmostEqual(sum(s['heat_w'] for s in thermal['axial_segments']),thermal['assumed_heat_load_w'])
        self.assertLess(abs(thermal['energy_balance_residual_w']),1e-6)
        self.assertTrue(candidate['engineering']['checks']['routed_cooling_energy_closure'])

    def test_lh2_constant_liquid_model_fails_outside_property_domain(self):
        engineering=design(RocketBrief(propellant_model='lox_lh2'))['candidates'][0]['engineering']
        self.assertGreater(engineering['thermal']['estimated_bulk_outlet_k'],32.976)
        self.assertFalse(engineering['checks']['fuel_property_domain'])
        self.assertFalse(engineering['analytical_screen_pass'])

    def test_geometry_audit_detects_disconnected_feed(self):
        candidate=design(RocketBrief())['candidates'][0]
        geometry=json.loads(json.dumps(candidate['geometry']))
        next(t for t in geometry['systems']['manifolds'] if t['id']=='fuel_feed')['bore_points'][-1][0]+=20
        audit=inspect_geometry(geometry)
        self.assertFalse(audit['pass'])
        self.assertFalse(audit['checks']['fuel_feed_to_cooling_inlet'])

    def test_pressure_fed_closure_and_variant_ranking(self):
        run=design(RocketBrief(jacket_pattern='none'))
        engineering=run['candidates'][0]['engineering']
        self.assertTrue(all(engineering['checks'].values()))
        self.assertEqual(len(run['alternatives']),3)
        self.assertEqual(run['alternatives'][0]['rank'],1)
        self.assertEqual(run['alternatives'][0]['channel_count'],engineering['channel_count'])
        self.assertLessEqual(run['alternatives'][0]['score'],run['alternatives'][1]['score'])
        tanks=run['candidates'][0]['geometry']['systems']['tanks']
        for tank,fluid in zip(tanks,('fuel','oxidizer')):
            required=engineering['tank_sizing'][fluid]
            self.assertEqual(tank['length_mm'],required['length_mm'])
            self.assertEqual(tank['radius_mm'],required['inner_radius_mm'])
        manifolds=run['candidates'][0]['geometry']['systems']['manifolds']
        self.assertEqual(manifolds[0]['bore_radius_mm'],engineering['feed_bore_radius_mm']['fuel'])
        self.assertNotEqual(manifolds[0]['points'][0],manifolds[0]['bore_points'][0])
        injector=run['candidates'][0]['geometry']['systems']['injector']
        self.assertEqual(len(injector['orifices']),2)
        self.assertAlmostEqual(injector['orifices'][0]['radius_mm'],engineering['injector_screen']['single_fuel_orifice_radius_mm'])
        schedule=engineering['pressurization_screen']['pressure_schedule']
        self.assertEqual(schedule[0]['regulated_tank_pressure_bar'],schedule[-1]['regulated_tank_pressure_bar'])
        self.assertGreater(schedule[0]['source_pressure_bar'],schedule[-1]['source_pressure_bar'])
        self.assertGreater(engineering['thermal']['estimated_hot_wall_k'],engineering['thermal']['estimated_bulk_outlet_k'])

    def test_pressure_shortfall_is_reported(self):
        run=design(replace(RocketBrief(),tank_pressure_bar=24))
        engineering=run['candidates'][0]['engineering']
        self.assertFalse(engineering['checks']['pressure_margin'])
        self.assertFalse(engineering['analytical_screen_pass'])
        self.assertTrue(all(not alternative['screen_pass'] for alternative in run['alternatives']))

    def test_each_ranked_variant_has_a_distinct_native_recipe(self):
        runs=[design(replace(RocketBrief(),channel_variant=n)) for n in (8,12,16)]
        self.assertEqual([r['candidates'][0]['engineering']['channel_count'] for r in runs],[8,12,16])
        self.assertEqual(len({r['candidates'][0]['id'] for r in runs}),3)
        self.assertTrue(all(sum(v['selected'] for v in r['alternatives'])==1 for r in runs))

    def test_calibration_is_not_claimed_without_measurements(self):
        run=design(RocketBrief())
        self.assertEqual(run['calibration']['status'],'awaiting_measured_data')
        self.assertEqual(run['execution']['calibration'],'awaiting_measured_data')

    def test_matching_evidence_reports_residual_without_fitting(self):
        run=design(RocketBrief());candidate=run['candidates'][0]
        prediction=candidate['engineering']['pressure_bar']['fuel_required']
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'data'/'evidence') as directory:
            path=Path(directory)/'observations.json'
            path.write_text(json.dumps([{'candidate_id':candidate['id'],'source':'instrumented test report',
                                         'date':'2026-10-19','measurements':{'fuel_required_tank_bar':prediction+1}}]))
            result=compare(candidate['id'],candidate['engineering'],path)
        self.assertEqual(result['status'],'comparison_only_no_parameter_fit')
        self.assertAlmostEqual(result['comparisons'][0]['residual'],-1)

    def test_passages_require_real_wall_budget(self):
        with self.assertRaises(ValueError):
            RocketBrief.parse({'wall_mm':4,'cooling_passages':1})

    def test_vehicle_flight_uses_engine_mass_flow_and_rocket_equation(self):
        brief=replace(RocketBrief(),payload_mass_kg=0,vehicle_drag_coefficient=0,target_apogee_m=150)
        performance=solve(brief)
        flight=screen_flight(brief,performance)
        self.assertAlmostEqual(flight['propellant_mass_kg'],performance['mass_flow_kg_s']*brief.burn_duration_s)
        self.assertAlmostEqual(flight['vacuum_ideal_delta_v_m_s'],flight['vacuum_thrust_n']/performance['mass_flow_kg_s']*math.log(flight['launch_mass_kg']/brief.vehicle_dry_mass_kg))
        self.assertLess(flight['pad_thrust_n'],flight['vacuum_thrust_n'])
        self.assertLess(flight['burnout_speed_m_s'],flight['vacuum_ideal_delta_v_m_s'])
        self.assertGreater(flight['predicted_apogee_m'],flight['burnout_altitude_m'])
        self.assertFalse(flight['target_screen_pass'])
        self.assertGreater(flight['suggested_minimum_ideal_thrust_n'],brief.thrust_n)

if __name__=='__main__':unittest.main()
