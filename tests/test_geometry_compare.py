import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from vega.geometry_compare import compare_runs

ROOT=Path(__file__).resolve().parents[1]


def study(root, identity, body_bytes, payload):
    directory=Path(root)/'data'/'native'
    directory.mkdir(parents=True,exist_ok=True)
    stl=b'vega'.ljust(80,b'\0')+struct.pack('<I',len(body_bytes))+b''.join(body_bytes)
    (directory/f'{identity}.assembly.stl').write_bytes(stl)
    bodies=[{'component_id':f'part_{i}','first_triangle':i,'triangle_count':1,'group':'core'} for i in range(len(body_bytes))]
    return {'id':identity,'requirements':{'payload_mass_kg':payload},
            'assembly_artifact':{'stl_sha256':hashlib.sha256(stl).hexdigest(),'bodies':bodies,
                                 'components':[{'id':f'part_{i}','name':f'Part {i}'} for i in range(len(body_bytes))]}}


class GeometryCompareTests(unittest.TestCase):
    def test_exact_changed_body_and_mission_only_input(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as root:
            self.assertTrue(Path(root).resolve().is_relative_to(ROOT.resolve()))
            a=study(root,'a'*32,[bytes(50),bytes([1])*50],1000)
            b=study(root,'b'*32,[bytes(50),bytes([2])*50],2000)
            result=compare_runs(a,b,root)
            self.assertEqual(result['status'],'changed')
            self.assertEqual(result['changed_component_count'],1)
            self.assertEqual(result['components'][1]['status'],'changed')
            self.assertEqual(result['changed_inputs'][0]['geometry_dependency'],'mission_only')

    def test_same_bytes_are_unchanged(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as root:
            self.assertTrue(Path(root).resolve().is_relative_to(ROOT.resolve()))
            a=study(root,'a'*32,[bytes(50)],1000)
            b=study(root,'b'*32,[bytes(50)],1000)
            result=compare_runs(a,b,root)
            self.assertEqual(result['status'],'unchanged')
            self.assertEqual(result['changed_component_count'],0)


if __name__=='__main__':unittest.main()
