import unittest
from dataclasses import replace
from vega.preview import geometry_preview
from vega.rocket import RocketBrief


class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief=RocketBrief(propellant_model='assumed',jacket_pattern='none')
        cls.baseline=geometry_preview(cls.brief)

    def test_recipe_parts_partition_preview(self):
        p=self.baseline;cursor=0;ids=set()
        self.assertEqual(p['kind'],'unsaved_recipe_preview')
        for body in p['scene']['bodies']:
            self.assertEqual(body['first_triangle'],cursor)
            self.assertNotIn(body['component_id'],ids);ids.add(body['component_id'])
            cursor+=body['triangle_count']
        self.assertEqual(cursor,len(p['scene']['triangles']))
        self.assertIn('core_fuel_tank',ids);self.assertIn('core_oxidizer_feed',ids)
        self.assertIn('Cooling cuts',p['scope'])

    def test_engine_requirement_changes_preview_geometry(self):
        p=geometry_preview(replace(self.brief,chamber_length_mm=180))
        self.assertNotEqual(p['geometry_sha256'],self.baseline['geometry_sha256'])

    def test_mission_only_edit_does_not_invent_engine_changes(self):
        p=geometry_preview(replace(self.brief,payload_mass_kg=2000))
        self.assertEqual(p['geometry_sha256'],self.baseline['geometry_sha256'])
        self.assertNotEqual(p['vehicle_screen'],self.baseline['vehicle_screen'])
