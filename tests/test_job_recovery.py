import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class JobRecoveryTests(unittest.TestCase):
    def test_running_job_is_interrupted_after_restart_and_keeps_outputs(self):
        identity = 'a' * 32
        with tempfile.TemporaryDirectory(dir=server.ROOT / 'tmp') as directory, patch.object(server, 'DATA', Path(directory)), patch.object(server, 'JOBS', {}):
            server.save_job(identity, {'status': 'running', 'available_run_ids': ['b' * 32]})
            state = server.job_state(identity)
            self.assertEqual(state['status'], 'interrupted')
            self.assertEqual(state['available_run_ids'], ['b' * 32])
            server.JOBS.clear()
            self.assertEqual(server.job_state(identity)['status'], 'interrupted')

    def test_invalid_id_is_not_used_as_a_path(self):
        self.assertEqual(server.job_state('../outside'), {'status': 'unknown'})

    def test_failure_keeps_existing_job_metadata_on_disk(self):
        identity = 'a' * 32
        with tempfile.TemporaryDirectory(dir=server.ROOT / 'tmp') as directory, patch.object(server, 'DATA', Path(directory)), patch.object(server, 'JOBS', {identity: {'available_run_ids': ['b' * 32]}}), patch.object(server, 'evaluate_design', side_effect=ValueError('worker stopped')):
            server.run_job(identity, object())
            server.JOBS.clear()
            state = server.job_state(identity)
            self.assertEqual(state['status'], 'failed')
            self.assertEqual(state['error'], 'worker stopped')
            self.assertEqual(state['available_run_ids'], ['b' * 32])


class CancellationTests(unittest.TestCase):
    def test_cancel_is_durable_and_late_worker_cannot_replace_it(self):
        identity='c'*32
        with tempfile.TemporaryDirectory(dir=server.ROOT/'tmp') as directory, patch.object(server,'DATA',Path(directory)), patch.object(server,'JOBS',{identity:{'status':'queued','available_run_ids':['d'*32]}}):
            state=server.cancel_job(identity)
            self.assertEqual(state['status'],'cancelled')
            with patch.object(server,'evaluate_design',side_effect=AssertionError('must not launch')):
                server.run_job(identity,object())
            server.JOBS.clear()
            self.assertEqual(server.job_state(identity)['status'],'cancelled')
            self.assertEqual(server.job_state(identity)['available_run_ids'],['d'*32])

    def test_cancel_does_not_replace_completed_result(self):
        identity='e'*32
        with patch.object(server,'JOBS',{identity:{'status':'complete','run_id':identity}}):
            self.assertEqual(server.cancel_job(identity)['status'],'complete')
