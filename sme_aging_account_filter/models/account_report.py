from odoo import models, fields, api, _

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    filter_accounts = None

