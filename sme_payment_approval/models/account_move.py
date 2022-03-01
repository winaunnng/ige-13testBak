from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('submit', 'To Approve'),
            ('approve','Approved'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
