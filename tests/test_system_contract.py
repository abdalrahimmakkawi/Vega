import copy
import unittest

from vega.rocket import RocketBrief, design
from vega.system_contract import build_system_contract


def with_export_stubs(run):
    result=copy.deepcopy(run)
    candidate=result['candidates'][0]
    result['id']='0'*32
    result['artifact']={'scene_sha256':'test-core-scene'}
    assembly=candidate['assembly']
    assembly['scene']['triangles']=[[0,0,0] for _ in assembly['components']]
    for i,body in enumerate(assembly['scene']['bodies']):
        body['first_triangle']=i;body['triangle_count']=1
    bodies=[{**p,'first_triangle':i,'triangle_count':1} for i,p in enumerate(assembly['scene']['bodies'])]
    assembly_triangle_count=len(bodies)
    bodies.extend({'component_id':'core_'+p['id'],'first_triangle':assembly_triangle_count+i,
                   'triangle_count':1,'group':'core'} for i,p in enumerate(candidate['components']))
    result['artifact']['scene_triangles']=len(candidate['components'])
    total=len(bodies)
    result['assembly_artifact']={'bodies':bodies,'recipe_sha256':assembly['recipe_sha256'],
        'source_core_scene_sha256':'test-core-scene','stl_sha256':'test-assembly-mesh',
        'triangles':total,'components':[]}
    return result


class SystemContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study=with_export_stubs(design(RocketBrief(propellant_model='assumed',
            inlet_capture_area_m2=.08,inlet_length_m=.6)))

    def test_registered_routes_drive_flow_and_every_body_has_lineage(self):
        contract=build_system_contract(self.study)
        self.assertTrue(all(contract['checks'].values()))
        self.assertEqual(len(contract['components']),len(self.study['assembly_artifact']['bodies']))
        edges=contract['flow']['edges']
        self.assertIn(['fuel_tank','fuel_feed'],edges)
        self.assertIn(['fuel_feed','cooling'],edges)
        self.assertIn(['cooling','fuel_return'],edges)
        self.assertIn(['fuel_return','injector'],edges)
        self.assertIn(['oxidizer_tank','oxidizer_feed'],edges)

    def test_mismatched_export_is_rejected(self):
        altered=copy.deepcopy(self.study)
        altered['assembly_artifact']['source_core_scene_sha256']='wrong-scene'
        with self.assertRaisesRegex(ValueError,'native_core_scene_matches_export'):
            build_system_contract(altered)

    def test_missing_route_edge_is_rejected(self):
        altered=copy.deepcopy(self.study)
        altered['candidates'][0]['assembly']['topology']['flow']['edges'].remove(['fuel_feed','cooling'])
        with self.assertRaisesRegex(ValueError,'all_propellant_edges_from_registered_routes'):
            build_system_contract(altered)

    def test_disconnected_vehicle_mass_is_rejected(self):
        altered=copy.deepcopy(self.study)
        altered['candidates'][0]['vehicle_screen']['vehicle']['dry_mass_excluding_payload_kg']+=10
        with self.assertRaisesRegex(ValueError,'mission_dry_mass_matches_selected_mass_model'):
            build_system_contract(altered)

    def test_resource_mass_cannot_disappear_from_vehicle_budget(self):
        altered=copy.deepcopy(self.study)
        altered['candidates'][0]['orbital_resources']['component_masses_kg']['solar_arrays']*=2
        with self.assertRaisesRegex(ValueError,'orbital_resource_masses_in_vehicle_budget'):
            build_system_contract(altered)

    def test_component_mesh_ranges_must_cover_the_complete_export(self):
        altered=copy.deepcopy(self.study)
        altered['assembly_artifact']['bodies'][2]['first_triangle']+=1
        with self.assertRaisesRegex(ValueError,'exported_component_triangle_ranges_partition_mesh'):
            build_system_contract(altered)

    def test_core_only_export_is_checked_without_a_combined_cycle_assembly(self):
        run=design(RocketBrief(propellant_model='assumed',propulsion_family='rocket_only',jacket_pattern='none'))
        parts=run['candidates'][0]['components']
        run['artifact']={'scene_sha256':'core','scene_triangles':len(parts),
                         'bodies':[{'component_id':p['id'],'first_triangle':i,'triangle_count':1} for i,p in enumerate(parts)]}
        contract=build_system_contract(run)
        self.assertEqual(len(contract['components']),len(parts))
        run['artifact']['bodies'][0]['first_triangle']=1
        with self.assertRaisesRegex(ValueError,'exported_component_triangle_ranges_partition_mesh'):
            build_system_contract(run)


if __name__=='__main__':unittest.main()
