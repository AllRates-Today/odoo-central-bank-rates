# Part of the AllRatesToday Odoo connector. See LICENSE (LGPL-3).
"""Pure helpers with no Odoo import, so the direction logic is unit-testable
outside an Odoo instance (``python3 -m unittest`` from the addon root).

The AllRatesToday central-bank table is a list of rows
``{"base": "EUR", "quote": "USD", "type": "reference", "value": 1.17}``
where ``value`` is always *quote units per 1 base unit*. Publishers differ in
which side their home currency sits on: the ECB prints foreign per 1 EUR
(base EUR), the RBI prints INR per 1 foreign unit (quote INR). Odoo's
``_generate_currency_rates`` needs every rate on one common base and rebases
to the company currency itself, so this module normalises the table to
"units of X per 1 pivot currency" and lets Odoo do the rest.
"""
from collections import Counter

# Rate-type labels the AllRatesToday ingest emits today, most-general first.
# Used only to break ties when one bank prints several series (buy/sell/middle)
# for the same pair; the operator can pin one via the rate_type parameter.
RATE_TYPE_PREFERENCE = (
    'reference',
    'middle',
    'indicative',
    'monthly',
    'monthly_average',
    'quarterly',
    'close',
    'informational',
    'buy',
    'sell',
)


def pick_pivot(rows, preferred=()):
    """Return the currency code shared by the most rows (the publisher's home
    currency). ``preferred`` (e.g. the company currencies) breaks ties, which
    only matters for a table of a single row."""
    counts = Counter()
    for row in rows:
        counts[row['base']] += 1
        counts[row['quote']] += 1
    if not counts:
        return None
    preferred = set(preferred)
    return sorted(counts, key=lambda c: (-counts[c], c not in preferred, c))[0]


def _type_rank(rate_type):
    try:
        return RATE_TYPE_PREFERENCE.index(rate_type)
    except ValueError:
        return len(RATE_TYPE_PREFERENCE)


def normalise_table(rows, available_currency_names, date_rate, preferred_pivots=(), rate_type=None):
    """Turn an AllRatesToday ``rates`` list into the dict Odoo's
    ``_parse_<provider>_data`` must return: ``{code: (rate, date)}`` with every
    rate expressed as units of ``code`` per 1 pivot currency and the pivot
    itself at 1.0.

    - rows where neither side is the pivot are skipped (nothing to anchor on);
    - when the pivot is the *quote* side (RBI-style) the value is inverted;
    - ``rate_type`` pins one of the bank's series; otherwise the best-ranked
      type available for each pair wins (see RATE_TYPE_PREFERENCE).
    """
    available = set(available_currency_names)
    pivot = pick_pivot(rows, preferred_pivots)
    if pivot is None:
        return {}

    best = {}  # other currency -> (type rank, rate)
    for row in rows:
        row_type = row.get('type')
        if rate_type and row_type != rate_type:
            continue
        value = row.get('value')
        if not isinstance(value, (int, float)) or value <= 0:
            continue
        if row['base'] == pivot:
            other, rate = row['quote'], float(value)
        elif row['quote'] == pivot:
            other, rate = row['base'], 1.0 / float(value)
        else:
            continue
        if other == pivot or other not in available:
            continue
        rank = _type_rank(row_type)
        if other not in best or rank < best[other][0]:
            best[other] = (rank, rate)

    result = {code: (rate, date_rate) for code, (_rank, rate) in best.items()}
    if result and pivot in available:
        result[pivot] = (1.0, date_rate)
    return result
