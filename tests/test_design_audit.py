import unittest
from copy import deepcopy
from vega.demonstrator import recipe
from vega.design_audit import arithmetic_checks,route_conflicts,require_route_clearance
from vega.architecture import modules
from vega.bell_cooling import geometry,input_parts
from vega.integration import specification


class DesignAuditTests(unittest.TestCase):
    def test_corrected_service_layout_has_distinct_terminals_and_no_route_overlap(self):
        design=recipe();design['architecture_modules']=modules()
        added,joints=input_parts(design,geometry(design));inherited,_=specification()
        replaced={p['id'] for p in added}
        parts=[p for p in inherited if p['id'] not in replaced]+added
        self.assertEqual(route_conflicts(parts),[])
        hydrogen=next(p for p in parts if p['id']=='hydrogen-line')
        helium=next(p for p in parts if p['id']=='helium-link')
        self.assertNotEqual(hydrogen['routes'][0]['points'][-1],helium['routes'][0]['points'][-1])
        self.assertTrue(any(j['part']=='hydrogen-line' and j['source']=='pre-burner' for j in joints))

    def test_arithmetic_detects_changed_saved_result(self):
        design=recipe()
        self.assertTrue(all(c['passed'] for c in arithmetic_checks(design)))
        design['synthesis']['equations'][2]['outputs']['shaft_power_w']*=2
        failures=[c['quantity'] for c in arithmetic_checks(design) if not c['passed']]
        self.assertEqual(failures,['reference_compressor_power_w'])

    def test_route_crossing_shared_terminal_and_clear_routes(self):
        def part(name,points):return dict(id=name,routes=[dict(points=points,outer=1.,bore=.5)])
        a=part('a',[[-10,0,0],[10,0,0]])
        b=part('b',[[0,-10,0],[0,10,0]])
        self.assertEqual(route_conflicts([a,b])[0]['kind'],'route_crossing')
        with self.assertRaisesRegex(ValueError,'a / b'):require_route_clearance([a,b])
        b['routes'][0]['points']=[[10,0,0],[10,10,0]]
        self.assertEqual(route_conflicts([a,b])[0]['kind'],'shared_terminal')
        b['routes'][0]['points']=[[0,-10,3],[0,10,3]]
        self.assertEqual(route_conflicts([a,b]),[])
        require_route_clearance([a,b])

