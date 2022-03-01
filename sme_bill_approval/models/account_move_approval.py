# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class Company(models.Model):
    _inherit = 'res.company'

    account_move_individual_approval = fields.Boolean(string='Bill Individual Approval')


class AccountMove(models.Model):
    _inherit = "account.move"
    _description = "Journal Entries ( Invoice/Bill )"

    account_move_individual_approval = fields.Boolean(string='Bill Individual Approval',
                                            related='company_id.account_move_individual_approval')

    @api.model
    def _get_default_currency(self):
        ''' Get the default currency from either the journal, either the default journal's company. '''
        journal = self._get_default_journal()
        return journal.currency_id or journal.company_id.currency_id

    @api.model
    def _get_default_journal(self):
        ''' Get the default journal.
        It could either be passed through the context using the 'default_journal_id' key containing its id,
        either be determined by the default type.
        '''
        move_type = self._context.get('default_move_type', 'entry')
        if move_type in self.get_sale_types(include_receipts=True):
            journal_types = ['sale']
        elif move_type in self.get_purchase_types(include_receipts=True):
            journal_types = ['purchase']
        else:
            journal_types = self._context.get('default_move_journal_types', ['general'])

        if self._context.get('default_journal_id'):
            journal = self.env['account.journal'].browse(self._context['default_journal_id'])

            if move_type != 'entry' and journal.type not in journal_types:
                raise UserError(_(
                    "Cannot create an invoice of type %(move_type)s with a journal having %(journal_type)s as type.",
                    move_type=move_type,
                    journal_type=journal.type,
                ))
        else:
            journal = self._search_default_journal(journal_types)

        return journal


    @api.model
    def _get_default_invoice_date(self):
        return fields.Date.context_today(self) if self._context.get('default_type', 'entry') in self.get_purchase_types(include_receipts=True) else False

    date = fields.Date(
        string='Date',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)],'submit': [('readonly', False)]},
        copy=False,
        tracking=True,
        default=fields.Date.context_today
    )
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True,
                                 states={'draft': [('readonly', False)],'submit': [('readonly', False)]},
                                 check_company=True, domain="[('id', 'in', suitable_journal_ids)]",
                                 default=_get_default_journal)

    currency_id = fields.Many2one('res.currency', store=True, readonly=True, tracking=True, required=True,
        states={'draft': [('readonly', False)],'submit': [('readonly', False)]},
        string='Currency',
        default=_get_default_currency)
    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items', copy=True, readonly=True,
        states={'draft': [('readonly', False)],'submit': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', readonly=True, tracking=True,
        states={'draft': [('readonly', False)],'submit': [('readonly', False)]},
        check_company=True,
        string='Partner', change_default=True)

    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True,
        states={'draft': [('readonly', False)],'submit': [('readonly', False)]},
        check_company=True,
        domain="[('company_id', '=', company_id)]", ondelete="restrict",
        help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices. "
             "The default value comes from the customer.")

    invoice_date = fields.Date(string='Invoice/Bill Date', readonly=True, index=True, copy=False,
        states={'draft': [('readonly', False)],'submit': [('readonly', False)]})

    invoice_date_due = fields.Date(string='Due Date', readonly=True, index=True, copy=False,
        states={'draft': [('readonly', False)],'submit': [('readonly', False)]})

    invoice_line_ids = fields.One2many('account.move.line', 'move_id', string='Invoice lines',
        copy=False, readonly=True,
        domain=[('exclude_from_invoice_tab', '=', False)],
        states={'draft': [('readonly', False)],'submit': [('readonly', False)]})

    approver_ids = fields.One2many('account.move.approver', 'move_id', string="Approvers")
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('submit', 'To Approve'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled')
    ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')

    user_status = fields.Selection([
        ('draft', 'RFQ'),
        ('submit', 'To Approve'),
        ('posted', 'Approved'),
        ('cancel', 'Cancelled')], compute="_compute_user_status")


    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        user = self.env.user
        for move in self:
            move.user_status = move.approver_ids.filtered(lambda r: r.user_id == user).status

    def action_submit(self):
        for move in self:
            # one by one request approval
            if move.get_approver():
                move.request_approval(self.get_approver())
                move.write({'state': 'submit'})
            else:
                type = 'bill' if move.type =='in_invoice' else 'journal entry'
                raise UserError(_("You have to add at least one approver to submit your " + type + " request."))

    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'account.move'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('sme_bill_approval.mail_activity_data_bill_approval').id),
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
        approver.write({'status': 'posted'})
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()

        # one by one request approval
        next_approver = self.get_approver()
        if next_approver:
            self.request_approval(next_approver)

        status_lst = self.mapped('approver_ids.status')
        approvers = len(status_lst)
        result ={}
        if status_lst.count('posted') == approvers:
            self.action_post()
            type = 'Bill' if self.move_type == 'in_invoice' else 'Journal Entry'
            ref = _("( Ref - %s )") % self.ref if self.ref else ''
            if self.user_id:
                self.message_notify(
                    partner_ids=self.user_id.partner_id.ids,
                    body=_("Your %s %s has been approved by the name of %s") % (type,ref,self.name,),subject=self.name)
            # self.message_post_with_view('sme_bill_approval.account_move_template_approve',
            #                             values={'ref': self.ref,'name': self.name,'type': self.type})
        return result


    def request_approval(self,approver):
        approver._create_activity()
        approver.write({'status': 'submit'})


    def refuse_move(self,reason,force=False,approver=None,):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        if approver:
            approver.write({'status': 'cancel'})
            self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
            self.message_post_with_view('sme_bill_approval.account_move_template_refuse_reason',
                                   values={'reason': reason,'name': self.name,'ref': self.ref,'type': self.move_type})
        status_lst = self.mapped('approver_ids.status')
        approvers = len(status_lst)
        result = {}
        # if status_lst.count('cancel') == approvers:
        self.write({'state': 'cancel'})
        return result

    def button_draft(self):
        super(AccountMove, self).button_draft()
        if self.approver_ids:
            self.approver_ids.write({'status':'draft'})
            self.activity_unlink(['sme_bill_approval.mail_activity_data_bill_approval'])


class AccountMoveApprover(models.Model):
    _name = 'account.move.approver'
    _description = 'Bill Approver'
    _order = 'move_id,id'


    user_id = fields.Many2one('res.users', string="User", required=True)
    name = fields.Char(related='user_id.name')
    status = fields.Selection([
        ('draft', 'New'),
        ('submit', 'To Approve'),
        ('posted', 'Approved'),
        ('cancel', 'Refused')
       ], string="Status", default="draft", readonly=True)
    move_id = fields.Many2one('account.move', string="Bill", ondelete='cascade')


    def button_approve(self):
        self.move_id.button_approve(self)

    def action_create_activity(self):
        self.write({'status': 'submit'})
        self._create_activity()

    def _create_activity(self):
        for approver in self:
            approver.move_id.activity_schedule(
                'sme_bill_approval.mail_activity_data_bill_approval',
                user_id=approver.user_id.id)

    @api.onchange('user_id')
    def _onchange_approver_ids(self):
        return {'domain': {'user_id': [('id', 'not in', self.move_id.approver_ids.mapped('user_id').ids + self.move_id.user_id.ids)]}}
