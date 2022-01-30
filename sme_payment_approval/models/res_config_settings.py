# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class Company(models.Model):
    _inherit = 'res.company'

    vendor_payment_individual_approval = fields.Boolean(string='Vendor Payment Individual Approval',default=False)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vendor_payment_individual_approval = fields.Boolean("Vendor Payment Individual Approval",related='company_id.vendor_payment_individual_approval',
                                            default=False,readonly=False)
