# Part of the AllRatesToday Odoo connector. See LICENSE (LGPL-3).
"""Direction tests for tools.normalise_table. Fixture rows are real values from
the AllRatesToday keyless endpoint, tables dated 2026-10-09.

Inside Odoo this is collected by the normal test runner (--test-enable).
Outside Odoo run it as a file: ``python3 currency_rate_allratestoday/tests/test_tools.py``
(the relative import then falls back to loading tools.py by path)."""
import datetime
import unittest

try:
    from ..tools import normalise_table, pick_pivot
except ImportError:  # run as a plain file, no Odoo on the path
    import importlib.util
    import os
    _spec = importlib.util.spec_from_file_location(
        'tools', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools.py'))
    _tools = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_tools)
    normalise_table, pick_pivot = _tools.normalise_table, _tools.pick_pivot

DATE = datetime.date(2026, 10, 9)

# ECB style: base is the home currency, value = foreign units per 1 EUR.
ECB_ROWS = [
    {'base': 'EUR', 'quote': 'AUD', 'type': 'reference', 'value': 1.6052},
    {'base': 'EUR', 'quote': 'BRL', 'type': 'reference', 'value': 5.6086},
]

# RBI style: quote is the home currency, value = INR per 1 foreign unit.
RBI_ROWS = [
    {'base': 'AED', 'quote': 'INR', 'type': 'reference', 'value': 26.3049},
    {'base': 'EUR', 'quote': 'INR', 'type': 'reference', 'value': 108.4728},
]


class TestNormaliseTable(unittest.TestCase):

    def test_pivot_is_the_shared_currency(self):
        self.assertEqual(pick_pivot(ECB_ROWS), 'EUR')
        self.assertEqual(pick_pivot(RBI_ROWS), 'INR')

    def test_ecb_direction_kept(self):
        out = normalise_table(ECB_ROWS, ['EUR', 'AUD', 'BRL'], DATE)
        self.assertEqual(out['EUR'], (1.0, DATE))
        self.assertEqual(out['AUD'], (1.6052, DATE))
        self.assertEqual(out['BRL'], (5.6086, DATE))

    def test_rbi_direction_inverted(self):
        out = normalise_table(RBI_ROWS, ['INR', 'AED', 'EUR'], DATE)
        self.assertEqual(out['INR'], (1.0, DATE))
        self.assertAlmostEqual(out['EUR'][0], 1 / 108.4728)
        self.assertAlmostEqual(out['AED'][0], 1 / 26.3049)

    def test_rebasing_matches_odoo(self):
        # currency_rate_live divides every rate by the company currency's rate.
        # A EUR company on the RBI table must end up with INR per 1 EUR = 108.4728.
        out = normalise_table(RBI_ROWS, ['INR', 'AED', 'EUR'], DATE)
        base = out['EUR'][0]
        self.assertAlmostEqual(out['INR'][0] / base, 108.4728, places=6)
        self.assertAlmostEqual(out['AED'][0] / base, 108.4728 / 26.3049, places=6)

    def test_inactive_currencies_dropped(self):
        out = normalise_table(ECB_ROWS, ['EUR', 'AUD'], DATE)
        self.assertNotIn('BRL', out)
        self.assertIn('AUD', out)

    def test_pivot_not_active_is_not_added(self):
        out = normalise_table(ECB_ROWS, ['AUD', 'BRL'], DATE)
        self.assertNotIn('EUR', out)
        self.assertEqual(len(out), 2)

    def test_rows_without_pivot_skipped(self):
        rows = ECB_ROWS + [{'base': 'USD', 'quote': 'JPY', 'type': 'reference', 'value': 150.0}]
        out = normalise_table(rows, ['EUR', 'AUD', 'BRL', 'USD', 'JPY'], DATE)
        self.assertNotIn('USD', out)
        self.assertNotIn('JPY', out)

    def test_type_preference_and_pin(self):
        rows = [
            {'base': 'USD', 'quote': 'LKR', 'type': 'buy', 'value': 300.0},
            {'base': 'USD', 'quote': 'LKR', 'type': 'sell', 'value': 310.0},
            {'base': 'USD', 'quote': 'LKR', 'type': 'middle', 'value': 305.0},
            {'base': 'EUR', 'quote': 'LKR', 'type': 'middle', 'value': 350.0},
        ]
        out = normalise_table(rows, ['LKR', 'USD', 'EUR'], DATE)
        self.assertAlmostEqual(out['USD'][0], 1 / 305.0)          # middle beats buy/sell
        pinned = normalise_table(rows, ['LKR', 'USD', 'EUR'], DATE, rate_type='sell')
        self.assertAlmostEqual(pinned['USD'][0], 1 / 310.0)
        self.assertNotIn('EUR', pinned)                            # no 'sell' row for EUR

    def test_bad_values_ignored(self):
        rows = [{'base': 'EUR', 'quote': 'USD', 'type': 'reference', 'value': 0},
                {'base': 'EUR', 'quote': 'GBP', 'type': 'reference', 'value': None}]
        self.assertEqual(normalise_table(rows, ['EUR', 'USD', 'GBP'], DATE), {})

    def test_single_row_pivot_prefers_company_currency(self):
        rows = [{'base': 'USD', 'quote': 'KHR', 'type': 'reference', 'value': 4000.0}]
        self.assertEqual(pick_pivot(rows, preferred=['KHR']), 'KHR')
        self.assertEqual(pick_pivot(rows, preferred=['USD']), 'USD')


if __name__ == '__main__':
    unittest.main()
