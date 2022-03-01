# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning

class ResUsers(models.Model):
    _inherit = 'res.users'

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'location_security_stock_location_users',
        'user_id',
        'analytic_account_id','Allowed Analytic Accounts')



