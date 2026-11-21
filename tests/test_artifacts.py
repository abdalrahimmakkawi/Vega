import hashlib
import tempfile
import unittest
from pathlib import Path
from vega.artifacts import compact_stl,materialized_stl,artifact_digest,artifact_size,open_artifact

class ArtifactTests(unittest.TestCase):
    def test_lossless_storage_and_download_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'sample.stl';data=bytes(range(256))*4096;p.write_bytes(data)
            compact_stl(p)
            self.assertFalse(p.exists());self.assertEqual(artifact_size(p),len(data))
            self.assertEqual(artifact_digest(p),hashlib.sha256(data).hexdigest())
            with open_artifact(p) as stream:self.assertEqual(stream.read(),data)
            with materialized_stl(p,writeback=True) as work:work.write_bytes(data+b'changed')
            with open_artifact(p) as stream:self.assertEqual(stream.read(),data+b'changed')
            self.assertFalse(p.with_suffix('.working.stl').exists())
