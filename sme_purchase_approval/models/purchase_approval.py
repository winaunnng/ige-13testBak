# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Company(models.Model):
    _inherit = 'res.company'

    po_individual_approval = fields.Boolean(string='PO Individual Approval',default=False)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    approver_ids = fields.One2many('purchase.approver', 'order_id', string="Approvers")
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True,
        store = True, compute_sudo = True, )

    user_status = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancel')], compute="_compute_user_status")

    po_individual_approval = fields.Boolean(string='PO Individual Approval',related ='company_id.po_individual_approval')

    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        user = self.env.user
        for order in self:
            order.user_status = order.approver_ids.filtered(lambda r: r.user_id == user).status



    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'purchase.order'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('sme_purchase_approval.mail_activity_data_approval').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities

    def get_approver(self):
        approver =  self.mapped('approver_ids').filtered(lambda approver: approver.status in ('draft', 'sent'))
        if len(approver) > 1 :
            return approver[0]
        else:
            return approver

    def button_approve(self, force=False,approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'purchase'})
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()

        # one by one request approval
        next_approver = self.get_approver()
        if next_approver:
            self.request_approval(next_approver)

        status_lst = self.mapped('approver_ids.status')
        approvers = len(status_lst)
        result ={}
        if status_lst.count('purchase') == approvers:
            if self.user_id:
                self.message_notify(
                    partner_ids=self.user_id.partner_id.ids,
                    body=_("Your Purchase Order %s has been approved") % (self.name),subject=self.name)
            # self.message_post_with_view('sme_purchase_approval.purchase_template_approve', values={'name': self.name})
            result = super(PurchaseOrder, self).button_approve(force=force)
        return result


    def request_approval(self,approver):
        approver._create_activity()
        approver.write({'status': 'to approve'})


    def action_submit(self):
        for order in self:
            # one by one request approval
            if order.get_approver():
                order.request_approval(self.get_approver())
                order.write({'state': 'to approve'})
            else:
                raise UserError(_("You have to add at least one approver to confirm your purchase request."))


    def refuse_order(self,reason,force=False,approver=None,):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        if approver:
            approver.write({'status': 'cancel'})
            self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
            self.message_post_with_view('sme_purchase_approval.purchase_template_refuse_reason',
                                   values={'reason': reason,'name': self.name})
        self.write({'state': 'cancel'})

    def button_draft(self):
        super(PurchaseOrder, self).button_draft()
        if self.approver_ids:
            self.approver_ids.write({'status': 'draft'})
            self.activity_unlink(['sme_purchase_approval.mail_activity_data_approval'])
        return {}

class PurchaseApprover(models.Model):
    _name = 'purchase.approver'
    _description = 'Purchase Approver'
    _order = 'order_id,id'


    user_id = fields.Many2one('res.users', string="User", required=True)
    name = fields.Char(related='user_id.name')
    status = fields.Selection([
        ('draft', 'New'),
        ('sent', 'New'),
        ('to approve', 'To Approve'),
        ('purchase', 'Approved'),
        ('done', 'Locked'),
        ('cancel', 'Refused')
       ], string="Status", default="draft", readonly=True)
    order_id = fields.Many2one('purchase.order', string="Purchase Order", ondelete='cascade')


    def button_approve(self):
        self.order_id.button_approve(self)

    def action_create_activity(self):
        self.write({'status': 'to approve'})
        self._create_activity()

    def _create_activity(self):
        for approver in self:
            approver.order_id.activity_schedule(
                'sme_purchase_approval.mail_activity_data_approval',
                user_id=approver.user_id.id)

    @api.onchange('user_id')
    def _onchange_approver_ids(self):
        return {'domain': {'user_id': [('id', 'not in', self.order_id.approver_ids.mapped('user_id').ids + self.order_id.user_id.ids)]}}
    