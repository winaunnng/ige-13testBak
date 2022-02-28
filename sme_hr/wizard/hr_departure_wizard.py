# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    departure_reason = fields.Selection([
        ('terminated', 'Contract Termination'),
        ('fired', 'Dismissed'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired'),
        ('transfer', 'Transfer'),
        ('retrenched', 'Retrenched')
    ], string="Separation Reason", default="fired")
