import json
import tempfile
import unittest
from pathlib import Path
from vega.run_index import run_summaries


class RunIndexTests(unittest.TestCase):
    def test_updates_only_when_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);identity='a'*32;path=root/(identity+'.json')
            run={'id':identity,'kind':'rocket','created_at':'2026-10-30',
                'requirements':{'thrust_n':1000,'propulsion_family':'rbcc'},
                'candidates':[{'engineering':{'channel_count':12}}]}
            path.write_text(json.dumps(run))
            self.assertEqual(run_summaries(root)[0]['thrust_n'],1000)
            self.assertEqual(run_summaries(root)[0]['channel_variant'],12)
            run['requirements']['thrust_n']=1100;path.write_text(json.dumps(run)+' ')
            self.assertEqual(run_summaries(root)[0]['thrust_n'],1100)
            path.unlink()
            self.assertEqual(run_summaries(root),[])


if __name__=='__main__':unittest.main()
