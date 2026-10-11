# Part of the AllRatesToday Odoo connector. See LICENSE (LGPL-3).
{
    'name': 'AllRatesToday: Official Central-Bank Currency Rates',
    'summary': 'Add AllRatesToday (121 central banks + 3 tax authorities) as a '
               'provider in Odoo\'s Automatic Currency Rates setting.',
    'description': """
Adds "AllRatesToday (official central-bank rates)" to the Service Provider list
of the Automatic Currency Rates setting (module currency_rate_live). Pick the
central bank or tax authority whose published table your company must use
(ECB, RBI, HMRC, ...), and Odoo's existing "Currency: rate update" cron writes
that bank's latest table into res.currency.rate in the direction Odoo expects.
""",
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'author': 'AllRatesToday',
    'website': 'https://allratestoday.com/docs/integrations/odoo/',
    'license': 'LGPL-3',
    'depends': [
        'currency_rate_live',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'data/ir_config_parameter_data.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
