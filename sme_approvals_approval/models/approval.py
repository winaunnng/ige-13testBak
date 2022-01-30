# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api,fields, models, tools, _

CATEGORY_SELECTION = [
    ('required', 'Required'),
    ('optional', 'Optional'),
    ('no', 'None')]


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    has_priority = fields.Selection(CATEGORY_SELECTION, string="Has Priority", default="no", required=True)
    has_analytic_account = fields.Selection(CATEGORY_SELECTION, string="Has Analytic Account", default="no", required=True)



class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    def _default_currency_id(self):
        company_id = self.env.context.get('force_company') or self.env.context.get('company_id') or self.env.company.id
        return self.env['res.company'].browse(company_id).currency_id

    priority = fields.Selection([
            ('0', 'Low'),
            ('1', 'Medium'),
            ('2', 'High'),
            ('3', 'Very High'),
        ], string='Priority', index=True,default='0')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    currency_id = fields.Many2one('res.currency', string="Currency",default=_default_currency_id)

    has_priority = fields.Selection(related="category_id.has_priority")
    has_analytic_account = fields.Selection(related="category_id.has_analytic_account")
    request_status = fields.Selection([
        ('new', 'To Submit'),
        ('pending', 'Submitted'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], default="new", compute="_compute_request_status", store=True, compute_sudo=True,
        group_expand='_read_group_request_status')

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)


    @api.depends('approver_ids.status')
    def _compute_request_status(self):
        for request in self:
            status_lst = request.mapped('approver_ids.status')
            minimal_approver = request.approval_minimum if len(status_lst) >= request.approval_minimum else len(status_lst)
            if status_lst:
                if status_lst.count('cancel'):
                    status = 'cancel'
                elif status_lst.count('refused'):
                    status = 'refused'
                elif status_lst.count('pending'):
                    status = 'pending'
                elif status_lst.count('new'):
                    status = 'new'
                elif status_lst.count('approved') >= minimal_approver:
                    status = 'approved'
                else:
                    status = 'pending'
            else:
                status = 'new'
            request.request_status = status


    def get_approver(self):
        approver =  self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
        if len(approver) > 1 :
            return approver[0]
        else:
            return approver

    def request_approval(self,approver):
        approver._create_activity()
        approver.write({'status': 'pending'})


    def action_confirm(self):
        if len(self.approver_ids) < self.approval_minimum:
            raise UserError(_("You have to add at least %s approvers to confirm your request.") % self.approval_minimum)
        if self.requirer_document == 'required' and not self.attachment_number:
            raise UserError(_("You have to attach at lease one document."))

        if self.get_approver():
            self.request_approval(self.get_approver())
            self.write({'date_confirmed': fields.Datetime.now()})

    def check_approver_pending(self):
        if self.mapped('approver_ids').filtered(lambda approver: approver.status == 'pending' and approver.user_id != self.env.user ):
            return True

    def action_approve(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )

        next_approver = self.get_approver()
        if not self.check_approver_pending() and next_approver :
            self.request_approval(next_approver)

        approver.write({'status': 'approved'})
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()



    def action_refuse_request(self,reason,force=False,approver=None,):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'refused'})
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        ref = _("( Ref - %s )") % self.reason if self.reason else ''

        if self.request_owner_id:
            self._message_log(body=_("Approval request %s %s has been refused. <br/><br/> Reason : %s") % (
                self.name,ref ,reason),subject=self.name)

        # self.message_post_with_view('sme_approvals_approval.approval_template_refuse_reason',
        #                        values={'reason': reason,'name': self.name,'ref':self.reason})

    def action_cancel(self):
        self.sudo()._get_user_approval_activities(user=self.env.user).unlink()
        self.activity_unlink(['approvals.mail_activity_data_approval'])
        self.mapped('approver_ids').write({'status': 'cancel'})