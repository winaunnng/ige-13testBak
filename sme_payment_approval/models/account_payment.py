# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    approver_ids = fields.One2many('account.payment.approver', 'payment_id', string="Approvers")
    state = fields.Selection(selection=[('draft', 'Draft'),('submit', 'To Approve'),('approve', 'Approved'),('posted', 'Validated'),
                                        ('sent', 'Sent'), ('reconciled', 'Reconciled'), ('cancelled', 'Cancelled')],
                             readonly=True, default='draft', copy=False, string="Status",tracking=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True, states={'draft': [('readonly', False)],'submit': [('readonly', False)],'approve': [('readonly', False)]}, tracking=True, domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]")
    amount = fields.Monetary(string='Amount', required=True, readonly=True, states={'draft': [('readonly', False)],'submit': [('readonly', False)]},
                             tracking=True)
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], tracking=True, readonly=True,
                                    states={'draft': [('readonly', False)],'submit': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Partner', tracking=True, readonly=True,
                                 states={'draft': [('readonly', False)],'submit': [('readonly', False)]},
                                 domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    payment_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, readonly=True,
                               states={'draft': [('readonly', False)],'submit': [('readonly', False)],'approve': [('readonly', False)]}, copy=False, tracking=True)
    communication = fields.Char(string='Memo', readonly=True, states={'draft': [('readonly', False)],'submit': [('readonly', False)],'approve': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)],'submit': [('readonly', False)]}, default=lambda self: self.env.company.currency_id)

    user_status = fields.Selection(
        [('none', 'None'),
         ('draft', 'New'),
         ('submit', 'To Approve'),
         ('approve', 'Approve'),
         ('sent', 'Sent'),
         ('reconciled', 'Reconciled'),
         ('cancelled', 'Cancelled')], compute="_compute_user_status")

    vendor_payment_individual_approval = fields.Boolean(string='Vendor Payment Individual Approval',
                                            related='company_id.vendor_payment_individual_approval')

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
            ref = _("( Ref - %s )") % self.communication if self.communication else ''
            subject = self.name if self.name else 'Draft Payment(* '+ str(self.id) +')'
            self.message_notify(
                partner_ids=self.create_uid.partner_id.ids,
                body=_("Your Payment %s has been approved.") % (ref), subject= subject)
            # self.message_post_with_view('sme_payment_approval.payment_template_approve',
            #                             values={'name': self.name,'ref': self.communication})
            self.write({'state': 'approve'})
        # return result

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
                                   values={'reason': reason,'name': self.name,'ref': self.communication})
        status_lst = self.mapped('approver_ids.status')
        approvers = len(status_lst)
        result = {}
        # if status_lst.count('cancel') == approvers:
        self.write({'state': 'cancelled'})
        return result


    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconcilable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        AccountMove = self.env['account.move'].with_context(default_type='entry')
        for rec in self:

            if rec.state not in ('draft','submit','approve'):
                raise UserError(_("Only draft and approve payment can be posted."))

            if any(inv.state != 'posted' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # keep the name in case of a payment reset to draft
            if not rec.name:
                # Use the right sequence to set the name
                if rec.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                else:
                    if rec.partner_type == 'customer':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.customer.invoice'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund'
                    if rec.partner_type == 'supplier':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice'
                rec.name = self.env['ir.sequence'].next_by_code(sequence_code, sequence_date=rec.payment_date)
                if not rec.name and rec.payment_type != 'transfer':
                    raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

            moves = AccountMove.create(rec._prepare_payment_moves())
            moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()

            # Update the state / move before performing any reconciliation.
            move_name = self._get_move_name_transfer_separator().join(moves.mapped('name'))
            rec.write({'state': 'posted', 'move_name': move_name})

            if rec.payment_type in ('inbound', 'outbound'):
                # ==== 'inbound' / 'outbound' ====
                if rec.invoice_ids:
                    (moves[0] + rec.invoice_ids).line_ids \
                        .filtered(lambda line: not line.reconciled and line.account_id == rec.destination_account_id and not (line.account_id == line.payment_id.writeoff_account_id and line.name == line.payment_id.writeoff_label))\
                        .reconcile()
            elif rec.payment_type == 'transfer':
                # ==== 'transfer' ====
                moves.mapped('line_ids')\
                    .filtered(lambda line: line.account_id == rec.company_id.transfer_account_id)\
                    .reconcile()

        return True

    def read(self, fields):
        self.clear_caches()
        return super(AccountPayment, self).read(fields)

    def action_draft(self):
        super(AccountPayment, self).action_draft()
        if self.approver_ids:
            self.approver_ids.write({'status': 'draft'})
            self.activity_unlink(['sme_payment_approval.mail_activity_data_payment_approval'])
        return {}


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