# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ApprovalRefuseWizard(models.TransientModel):
    """This wizard can be launched from an he.expense (an expense line)
    or from an hr.expense.sheet (En expense report)
    'hr_expense_refuse_model' must be passed in the context to differentiate
    the right model to use.
    """

    _name = "approval.refuse.wizard"
    _description = "Approval Refuse Reason Wizard"

    reason = fields.Char(string='Reason', required=True)
    request_id = fields.Many2one('approval.request')

    @api.model
    def default_get(self, fields):
        res = super(ApprovalRefuseWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])
        res.update({
            'request_id': active_ids[0] if active_ids else False,

        })
        return res

    def approval_refuse_reason(self):
        self.ensure_one()
        if self.request_id:
            self.request_id.action_refuse_request(self.reason)
        return {'type': 'ir.actions.act_window_close'}
