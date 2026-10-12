# AllRatesToday for Odoo 17 — Official Central-Bank Exchange Rates

An Odoo 17 addon that plugs **AllRatesToday** into Odoo's built-in **Automatic Currency Rates** setting as one more *Service Provider*. Pick the central bank or tax authority your books must follow (ECB, Reserve Bank of India, HMRC, Swiss BAZG, ... 121 central banks and 3 tax authorities) and Odoo's existing daily cron loads that publisher's latest table into `res.currency.rate` in the direction Odoo expects.

[![Odoo 17.0](https://img.shields.io/badge/Odoo-17.0-714B67.svg)](https://github.com/odoo/odoo/tree/17.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/odoo/odoo/blob/17.0/setup.py)
[![License: LGPL-3](https://img.shields.io/badge/license-LGPL--3-blue.svg)](LICENSE)
[![Powered by AllRatesToday](https://img.shields.io/badge/Powered%20by-AllRatesToday-orange.svg)](https://allratestoday.com)

## 🚀 What it does

- 🏦 **One more provider, zero new plumbing** — adds `AllRatesToday (official central-bank rates)` to `res.company.currency_provider`, next to Odoo's own ECB, Bank of Canada, Banxico and friends. Interval, *Next Run* and the *Update now* button keep working unchanged.
- 🗺️ **Any publisher, not a fixed list** — Odoo 17 ships a fixed list of around twenty providers; this addon reads any of the [121 central banks and 3 tax authorities](https://allratestoday.com/central-bank-rates-api/) AllRatesToday covers, selected by a short bank code (`ecb`, `rbi`, `hmrc`, `bazg`, ...).
- 🧭 **Direction handled** — publishers quote either foreign-per-home (ECB) or home-per-foreign (RBI). Every row is normalised to the shape `currency_rate_live` requires and Odoo rebases it to your company currency itself (details below).
- 📅 **Dated with the bank's date** — `res.currency.rate.name` is the publisher's `rate_date`, never the run date; a rerun on the same date updates the row instead of duplicating it.
- 🔑 **Key or keyless** — with a free `art_live_...` key it reads the keyed `/api/v1/` table; with no key it reads the keyless evaluation copy at `/api/open/` (attribution terms are returned in that response).
- 🧪 **Testable without Odoo** — the direction logic lives in a pure module with unit tests on real published rows.

Standard Odoo extension points only: `fields.Selection(selection_add=...)` on `res.company`, a `_parse_<provider>_data(available_currencies)` method, `config_parameter=` settings fields and a view inheriting `currency_rate_live.res_config_settings_view_form`.

## 🏁 Install

Requirements: Odoo **17.0** with the `currency_rate_live` module available. `currency_rate_live` is part of Odoo Enterprise (it ships with the `account` app on Enterprise and Odoo.sh); on Community it is not present and this addon will not install.

```bash
# copy the addon into one of your addons paths
cp -r currency_rate_allratestoday /path/to/odoo/custom-addons/

# update the apps list and install (or use Apps > Update Apps List in the UI)
./odoo-bin -c odoo.conf -d <database> -i currency_rate_allratestoday --stop-after-init
```

Python dependency: `requests` (already required by Odoo itself).

Run the unit tests without an Odoo instance:

```bash
python3 currency_rate_allratestoday/tests/test_tools.py
```

## ⚙️ Setup

1. Get a free API key at <https://allratestoday.com/register> (keys look like `art_live_...`). You can skip this to evaluate with the keyless copy.
2. In Odoo go to **Accounting > Configuration > Settings > Currencies > Automatic Currency Rates**.
3. Set **Service** to *AllRatesToday (official central-bank rates)*. Three extra rows appear:

| Setting | `ir.config_parameter` key | Value |
| --- | --- | --- |
| Bank code | `currency_rate_allratestoday.bank` | Publisher short code, e.g. `ecb`, `rbi`, `hmrc`. Seeded `ecb`. Codes: [coverage map](https://allratestoday.com/central-bank-rates-api/) |
| API key | `currency_rate_allratestoday.api_key` | Your `art_live_...` key. Empty = keyless evaluation copy |
| Rate type | `currency_rate_allratestoday.rate_type` | Optional. Pin one of the bank's series when it prints several for a pair (`reference`, `middle`, `buy`, `sell`, ...) |

4. Set **Interval** to *Daily* (or *Monthly* for monthly publishers such as HMRC), save, and press the **Update now** (refresh) button once to load today's table.

Multi-company: the provider and the three parameters are database-wide; each company that selects *AllRatesToday* gets rates rebased to its own currency. Subsidiaries that must follow different publishers need separate databases or a per-company extension of `_allratestoday_settings()` in `models/res_company.py`.

## 🧭 Reading the numbers

The API returns rows `{"base", "quote", "type", "value"}` where `value` is always **quote units per 1 base unit**. Publishers differ in which side their home currency sits on:

| Publisher | Row as published | Meaning |
| --- | --- | --- |
| ECB (`ecb`) | `base: EUR, quote: USD, value: 1.1206` | 1 EUR = 1.1206 USD (foreign per 1 home) |
| RBI (`rbi`) | `base: EUR, quote: INR, value: 108.4728` | 1 EUR = 108.4728 INR (home per 1 foreign) |

Odoo stores `res.currency.rate.rate` as **units of the foreign currency per 1 unit of the company currency**. `currency_rate_live` asks each provider for a dict of rates on *any* single common base, including that base at `1.0`, and then divides every rate by the company currency's entry. This addon therefore:

1. Picks the **pivot**: the currency present on one side of the most rows — the publisher's home currency (EUR for the ECB, INR for the RBI). Company currencies break ties for single-row tables.
2. Keeps `value` when the pivot is the **base** side (ECB style) and inverts it (`1 / value`) when the pivot is the **quote** side (RBI style). Rows where neither side is the pivot are skipped.
3. Drops currencies that are not active in Odoo, picks the best-ranked `type` per pair (or the pinned one), and adds `pivot: 1.0`.
4. Returns the dict; Odoo rebases per company. A EUR company on the RBI table ends up with `INR = 108.4728` (INR per 1 EUR) and an INR company on the same table with `EUR = 0.009219`.

If the company currency does not appear in the chosen bank's table at all, Odoo raises its standard *"Your main currency (XXX) is not supported by this exchange rate provider"* error — choose a publisher that prints your currency.

The response also carries `rate_date`, `age_days`, `stale` and `cadence`. On weekends and holidays the most recent published `rate_date` is returned; a `stale` table is still loaded, with a warning in the Odoo log.

## 🔁 Scheduling

Nothing new to schedule. `currency_rate_live` already defines the `ir.cron` **Currency: rate update** (`res.company.run_update_currency()`, every 1 day). It runs for every company whose *Next Run* date is due and calls the selected provider's `_parse_<provider>_data`, so selecting *AllRatesToday* is enough. Set *Interval* to *Daily* for daily publishers and *Monthly* for monthly tables (HMRC, SNB monthly averages); `rate_date` is written as the effective date either way.

Each scheduled run is **one API request** per selected provider, which fits comfortably inside the free tier.

## 🏛️ Sources

AllRatesToday republishes the tables the publishers themselves put out: 121 central banks and 3 tax authorities (HMRC, the Swiss Federal Office for Customs and Border Security, the U.S. Treasury). The full list with codes, home currency and cadence is on the [central bank coverage map](https://allratestoday.com/central-bank-rates-api/); each publisher has its own page with the series it prints.

Disclaimer returned with every keyed response:

> Official rates as published by the named central bank. On weekends/holidays the most recent published rate_date is returned.

Endpoints this addon calls:

| Mode | Request | Auth |
| --- | --- | --- |
| Keyed | `GET https://allratestoday.com/api/v1/central-bank/{bank}/latest` | `Authorization: Bearer art_live_...` (the API also accepts `?api_key=`) |
| Keyless | `GET https://allratestoday.com/api/open/central-bank/{bank}` | none; evaluation copy with attribution terms in the body |

Dated tables, history and cross-computed pairs need a key; the Official Rates plan for finance teams is described at <https://allratestoday.com/pricing/#official>. Step-by-step guide and the XML-RPC alternative: <https://allratestoday.com/docs/integrations/odoo/>.

## 🤖 AI agents

- Hosted MCP endpoint, no key: `https://allratestoday.com/api/mcp` — official rates, history, cross-bank comparison and publication calendars as tools for Claude, Cursor and any Streamable HTTP MCP client.
- **Trial key for agents, no signup**: `POST https://allratestoday.com/api/agent/keys` (send `Content-Type: application/json`) returns a 100-call key valid 7 days, enough to try history and dated tables; both MCP servers expose it as `request_trial_key`
- Machine-readable site guide: <https://allratestoday.com/llms.txt>.
- An agent asked to "load the RBI reference rate into Odoo" can call the MCP `get_official_rates` tool to inspect the table and then set `currency_rate_allratestoday.bank = rbi` through Odoo's XML-RPC `ir.config_parameter.set_param`.

## 📜 License

[LGPL-3](LICENSE). Odoo is a trademark of Odoo S.A.; this addon is an independent integration and depends on the `currency_rate_live` module shipped with Odoo Enterprise.
