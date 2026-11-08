import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import server
from vega.design_search import SearchEvaluationError

class SearchJobFailureTests(unittest.TestCase):
    def test_failed_search_preserves_attempt_report(self):
        report={'search_seed':42,'attempts':[{'status':'rejected'}]}
        with tempfile.TemporaryDirectory(dir=server.ROOT/'tmp') as folder, patch.object(server,'DATA',Path(folder)), patch.object(server,'JOBS',{}), patch.object(server,'explore',side_effect=SearchEvaluationError('none',report)):
            server.search_job('a'*32,object())
            state=server.job_state('a'*32)
            self.assertEqual(state['status'],'failed')
            self.assertEqual(state['search_report'],report)
