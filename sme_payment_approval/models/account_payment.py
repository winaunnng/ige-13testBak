# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Company(models.Model):
    _inherit = 'res.company'

    vendor_payment_individual_approval = fields.Boolean(string='Vendor Payment Approval')


class AccountPayment(models.Model):
    _inherit = "account.payment"

    approver_ids = fields.One2many('account.payment.approver', 'payment_id', string="Approvers")
    user_status = fields.Selection(
        [('none', 'None'),
         ('draft', 'New'),
         ('submit', 'To Approve'),
         ('approve', 'Approve'),
         ('sent', 'Sent'),
         ('reconciled', 'Reconciled'),
         ('cancelled', 'Cancelled')], compute="_compute_user_status")

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    vendor_payment_individual_approval = fields.Boolean(related='company_id.vendor_payment_individual_approval',string='Vendor Payment Approval',readony=True)

    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        user = self.env.user
        for payment in self:
            if payment.approver_ids:
                if payment.approver_ids.filtered(lambda r: r.user_id == user).status:
                    payment.user_status = payment.approver_ids.filtered(lambda r: r.user_id == user).status
                else:
                    payment.user_status = 'none'
            else:
                payment.user_status = 'none'

    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'account.payment'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('sme_payment_approval.mail_activity_data_payment_approval').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities

    def get_approver(self):
        approver = self.mapped('approver_ids').filtered(lambda approver: approver.status in ('draft', 'sent'))
        if len(approver) > 1:
            return approver[0]
        else:
            return approver

    def button_approve(self, force=False,approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'approve'})
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()

        # one by one request approval
        next_approver = self.get_approver()
        if next_approver:
            self.request_approval(next_approver)

        status_lst = self.mapped('approver_ids.status')
        approvers = len(status_lst)

        if status_lst.count('approve') == approvers:
            ref = _("( Ref - %s )") % self.ref if self.ref else ''
            subject = self.name if self.name else 'Draft Payment(* '+ str(self.id) +')'
            self.message_notify(
                partner_ids=self.create_uid.partner_id.ids,
                body=_("Your Payment %s has been approved.") % (ref), subject= subject)
            self.write({'state': 'approve'})

    def request_approval(self,approver):
        approver._create_activity()
        approver.write({'status': 'submit'})


    def action_submit(self):
        for payment in self:
            # one by one request approval
            if payment.get_approver():
                payment.request_approval(self.get_approver())
                payment.write({'state': 'submit'})
            else:
                raise UserError(_("You have to add at least one approver to validate your payment request."))

    def refuse_payment(self,reason,force=False,approver=None,):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        if approver:
            approver.write({'status': 'cancelled'})
            self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
            self.message_post_with_view('sme_payment_approval.payment_template_refuse_reason',
                                   values={'reason': reason,'name': self.name,'ref': self.ref})
        status_lst = self.mapped('approver_ids.status')
        result = {}
        self.write({'state': 'cancel'})
        return result

    def read(self, fields):
        self.clear_caches()
        return super(AccountPayment, self).read(fields)

    def action_draft(self):
        self.move_id.button_draft()
        if self.approver_ids:
            self.approver_ids.write({'status': 'draft'})
            self.activity_unlink(['sme_payment_approval.mail_activity_data_payment_approval'])
        return {}

    def action_post(self):
        ''' draft -> posted '''
        super(AccountPayment, self).action_post()
        self.write({'state': 'posted'})


    def cancel(self):
        super(AccountPayment, self).cancel()
        if self.approver_ids:
            self.approver_ids.write({'status': 'cancelled'})
            self.activity_unlink(['sme_payment_approval.mail_activity_data_payment_approval'])


class AccountPaymentApprover(models.Model):
    _name = 'account.payment.approver'
    _description = 'Payment Approver'
    _order = 'payment_id,id'


    user_id = fields.Many2one('res.users', string="User", required=True)
    name = fields.Char(related='user_id.name')
    status = fields.Selection(
        [('none', 'None'),
         ('draft', 'New'),
         ('submit', 'To Approve'),
         ('approve', 'Approve'),
         ('sent', 'Sent'),
         ('reconciled', 'Reconciled'),
         ('cancelled', 'Cancelled')
       ], string="Status", default="draft", readonly=True)
    payment_id = fields.Many2one('account.payment', string="Payment", ondelete='cascade')


    def button_approve(self):
        self.payment_id.button_approve(self)

    def action_create_activity(self):
        self.write({'status': 'submit'})
        self._create_activity()

    def _create_activity(self):
        for approver in self:
            approver.payment_id.activity_schedule(
                'sme_payment_approval.mail_activity_data_payment_approval',
                user_id=approver.user_id.id)

    @api.onchange('user_id')
    def _onchange_approver_ids(self):
        return {'domain': {'user_id': [('id', 'not in', self.payment_id.approver_ids.mapped('user_id').ids + self.env.user.ids)]}}