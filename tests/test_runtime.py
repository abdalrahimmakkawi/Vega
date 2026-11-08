import subprocess
import unittest
from unittest.mock import patch
from vega.runtime import readiness


class RuntimeTests(unittest.TestCase):
    def tearDown(self):
        readiness.cache_clear()

    def test_import_failure_does_not_report_healthy(self):
        readiness.cache_clear()
        failed = subprocess.CompletedProcess([], 1, '', 'Missing CAD binding')
        with patch('vega.runtime.subprocess.run', return_value=failed):
            report = readiness()
        self.assertFalse(report['ready'])
        self.assertEqual(report['status'], 'degraded')
        self.assertIn('Missing CAD binding', report['checks']['cadquery']['error'])

    def test_timeout_is_reported_without_crashing_health_endpoint(self):
        readiness.cache_clear()
        with patch('vega.runtime.subprocess.run', side_effect=subprocess.TimeoutExpired('probe', 45)):
            self.assertFalse(readiness()['ready'])
