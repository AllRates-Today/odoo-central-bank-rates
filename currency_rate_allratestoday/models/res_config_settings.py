# Part of the AllRatesToday Odoo connector. See LICENSE (LGPL-3).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # config_parameter= stores each value in ir.config_parameter under the
    # given key; res_company._allratestoday_settings() reads the same keys.
    allratestoday_api_key = fields.Char(
        string="AllRatesToday API Key",
        config_parameter='currency_rate_allratestoday.api_key',
        help="Free key from https://allratestoday.com/register (art_live_...). "
             "Leave empty to read the keyless evaluation copy at /api/open/.",
    )
    allratestoday_bank = fields.Char(
        string="AllRatesToday Bank Code",
        config_parameter='currency_rate_allratestoday.bank',
        help="Short code of the central bank or tax authority whose table to load, "
             "e.g. ecb, rbi, hmrc, bazg. Full list: https://allratestoday.com/central-bank-rates-api/",
    )
    allratestoday_rate_type = fields.Char(
        string="AllRatesToday Rate Type",
        config_parameter='currency_rate_allratestoday.rate_type',
        help="Optional. Pin one of the bank's series when it prints several for the same pair "
             "(e.g. reference, middle, buy, sell). Empty = best available per pair.",
    )
