# currency_rate_allratestoday

Odoo 17 addon that adds **AllRatesToday (official central-bank rates)** to the *Service Provider*
list of Odoo's **Automatic Currency Rates** setting (module `currency_rate_live`).

- Extends `res.company.currency_provider` with `('allratestoday', ...)` via `selection_add`.
- Implements `_parse_allratestoday_data(available_currencies)` with the contract `currency_rate_live`
  expects: `{currency_code: (rate, date)}`, all rates on one common base, base included at `1.0`.
  Odoo's own `_generate_currency_rates` then rebases to each company's currency and writes
  `res.currency.rate` rows dated with the bank's `rate_date`.
- Settings (stored in `ir.config_parameter`, editable under Accounting > Settings > Currencies when
  the provider is selected):

| Parameter | Setting label | Meaning |
| --- | --- | --- |
| `currency_rate_allratestoday.bank` | Bank code | Publisher to load, e.g. `ecb`, `rbi`, `hmrc`, `bazg` (seeded `ecb`) |
| `currency_rate_allratestoday.api_key` | API key | `art_live_...` key; empty = keyless evaluation copy (`/api/open/`) |
| `currency_rate_allratestoday.rate_type` | Rate type | Optional: pin one series (`reference`, `middle`, `buy`, `sell`, ...) |

Endpoints used: `GET https://allratestoday.com/api/v1/central-bank/{bank}/latest` (keyed, `Authorization: Bearer`)
or `GET https://allratestoday.com/api/open/central-bank/{bank}` (keyless).

Tests: `python3 currency_rate_allratestoday/tests/test_tools.py` (no Odoo needed) or Odoo's `--test-enable`.

Full documentation in the repository [README](../README.md) and the guide at
<https://allratestoday.com/docs/integrations/odoo/>. License: LGPL-3.
