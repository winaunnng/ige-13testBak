# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    po_individual_approval = fields.Boolean(related='company_id.po_individual_approval', string='Purchase Order Approval (Customized)', readonly=False)



