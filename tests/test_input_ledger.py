import unittest
from vega.component_network import input_ledger


class InputLedgerTests(unittest.TestCase):
    def test_ledger_counts_only_declared_missing_inputs(self):
        result = input_ledger({'source_recipe_sha256': 'a' * 64,
                               'outstanding_inputs': [{'input_id': 'x'}]})
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['missing_input_count'], 1)
        self.assertEqual(result['source_recipe_sha256'], 'a' * 64)


if __name__ == '__main__':
    unittest.main()
