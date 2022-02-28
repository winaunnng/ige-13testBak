# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expense_individual_approval = fields.Boolean("Expense Individual Approval",related='company_id.expense_individual_approval',
                                           readonly=False)



