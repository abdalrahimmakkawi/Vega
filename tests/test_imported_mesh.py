import tempfile
import unittest
from pathlib import Path
from vega.meshing.kernel import model
from vega.meshing.imported import mesh_solid


class ImportedMeshTests(unittest.TestCase):
    def test_step_import_has_positive_tetrahedra_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'part.step';output=Path(folder)/'part.msh'
            with model('cad-fixture') as g:
                g.model.occ.addBox(0,0,0,10,8,6);g.model.occ.synchronize();g.write(str(source))
            original=source.read_bytes()
            result=mesh_solid(source,output,3.)
            self.assertGreater(result['summary']['cells'],20)
            self.assertGreater(result['summary']['minimum_jacobian_mm3'],0)
            self.assertEqual(result['tetrahedra'].shape[1],4)
            self.assertEqual(source.read_bytes(),original)
            self.assertTrue(output.is_file())
            with self.assertRaises(ValueError):mesh_solid(source,source,3.)


if __name__=='__main__':unittest.main()
