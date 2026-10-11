# Part of the AllRatesToday Odoo connector. See LICENSE (LGPL-3).
import logging
import re

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..tools import normalise_table

_logger = logging.getLogger(__name__)

ALLRATESTODAY_BASE_URL = 'https://allratestoday.com'
PARAM_API_KEY = 'currency_rate_allratestoday.api_key'
PARAM_BANK = 'currency_rate_allratestoday.bank'
PARAM_RATE_TYPE = 'currency_rate_allratestoday.rate_type'
DEFAULT_BANK = 'ecb'
BANK_CODE_RE = re.compile(r'^[a-z0-9_]{2,32}$')


class ResCompany(models.Model):
    _inherit = 'res.company'

    # currency_rate_live defines currency_provider as a stored computed
    # Selection; selection_add extends it without touching the other
    # providers. On uninstall, companies on this provider fall back to the
    # ECB, the value currency_rate_live itself defaults to.
    currency_provider = fields.Selection(
        selection_add=[('allratestoday', 'AllRatesToday (official central-bank rates)')],
        ondelete={'allratestoday': lambda recs: recs.write({'currency_provider': DEFAULT_BANK})},
    )

    def _allratestoday_settings(self):
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = (ICP.get_param(PARAM_API_KEY) or '').strip()
        bank = (ICP.get_param(PARAM_BANK) or DEFAULT_BANK).strip().lower()
        rate_type = (ICP.get_param(PARAM_RATE_TYPE) or '').strip().lower() or None
        if not BANK_CODE_RE.match(bank):
            raise UserError(_(
                "AllRatesToday bank code %r is not valid. Use the short code from "
                "https://allratestoday.com/central-bank-rates-api/ (for example ecb, rbi, hmrc).",
                bank,
            ))
        return api_key, bank, rate_type

    def _parse_allratestoday_data(self, available_currencies):
        ''' Update the currencies from the latest table published by one central bank
            or tax authority, as served by AllRatesToday.

            Keyed:   GET https://allratestoday.com/api/v1/central-bank/{bank}/latest
                     (Authorization: Bearer <key>, or ?api_key= on the URL)
            Keyless: GET https://allratestoday.com/api/open/central-bank/{bank}
                     (evaluation copy; attribution terms are in the response)

            Both return {"bank", "rate_date", "age_days", "stale", "cadence",
            "rates": [{"base", "quote", "type", "value"}], ...} where value is quote
            units per 1 base unit. Publishers quote in either direction (ECB: base EUR;
            RBI: quote INR), so the table is normalised to units per 1 pivot currency
            (the bank's home currency, 1.0) and currency_rate_live's
            _generate_currency_rates rebases to each company's currency.
        '''
        api_key, bank, rate_type = self._allratestoday_settings()

        headers = {'Accept': 'application/json', 'User-Agent': 'odoo-currency_rate_allratestoday/17.0.1.0.0'}
        if api_key:
            request_url = f"{ALLRATESTODAY_BASE_URL}/api/v1/central-bank/{bank}/latest"
            headers['Authorization'] = f"Bearer {api_key}"
        else:
            request_url = f"{ALLRATESTODAY_BASE_URL}/api/open/central-bank/{bank}"

        response = requests.get(request_url, headers=headers, timeout=30)
        if response.status_code == 401:
            raise UserError(_("AllRatesToday rejected the API key. Check it under Accounting > Settings > Currencies, "
                              "or create a free key at https://allratestoday.com/register"))
        if response.status_code == 403:
            raise UserError(_("The AllRatesToday plan on this key does not include this endpoint: %s",
                              response.text[:300]))
        if response.status_code == 404:
            raise UserError(_("AllRatesToday has no published table for bank code %r. Codes are listed at "
                              "https://allratestoday.com/central-bank-rates-api/", bank))
        response.raise_for_status()
        data = response.json()

        rows = data.get('rates') or []
        if not rows or not data.get('rate_date'):
            raise UserError(_("AllRatesToday returned no rates for bank %r.", bank))
        date_rate = fields.Date.to_date(data['rate_date'])
        if data.get('stale'):
            _logger.warning(
                "AllRatesToday: %s table dated %s is flagged stale (age_days=%s, cadence=%s); loading it anyway.",
                bank, data['rate_date'], data.get('age_days'), data.get('cadence'))

        available_currency_names = available_currencies.mapped('name')
        rslt = normalise_table(
            rows,
            available_currency_names,
            date_rate,
            preferred_pivots=self.mapped('currency_id.name'),
            rate_type=rate_type,
        )
        if not rslt:
            raise UserError(_("None of the currencies published by %r on %s are active in this database.",
                              bank, data['rate_date']))
        return rslt
