from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class Company(models.Model):
    _inherit = 'res.company'

    expense_individual_approval = fields.Boolean(string='Expense Individual Approval',default=False)

class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    state = fields.Selection([
        ('draft', 'To Submit'),
        ('reported', 'To Approve'),
        ('approved', 'Approved'),
        ('done', 'Paid'),
        ('refused', 'Refused')
    ], compute='_compute_state', string='Status', copy=False, index=True, readonly=True, store=True,
        help="Status of the expense.")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]}, default=_default_employee_id, domain=lambda self: self._get_employee_id_domain(), check_company=True)


    @api.model
    def _get_employee_id_domain(self):
        res = [('id', '=', 0)]  # Nothing accepted by domain, by default

        if self.env.user.employee_id:
            employee = self.env.user.employee_id
            res = [('id', '=', employee.id), '|', ('company_id', '=', False),
                   ('company_id', '=', employee.company_id.id)]

        if self.user_has_groups('hr_expense.group_hr_expense_user') or self.user_has_groups(
                'account.group_account_user') or  self.user_has_groups('hr_expense.group_hr_expense_team_approver') or  self.user_has_groups('sme_expense_approval.group_hr_expense_request_user'):
            res = "['|', ('company_id', '=', False), ('company_id', '=', company_id)]"  # Then, domain accepts everything
        # elif self.user_has_groups('hr_expense.group_hr_expense_team_approver') and self.env.user.employee_ids:
        #     user = self.env.user
        #     employee = self.env.user.employee_id
        #     res = [
        #         '|', '|', '|',
        #         ('department_id.manager_id', '=', employee.id),
        #         ('parent_id', '=', employee.id),
        #         ('id', '=', employee.id),
        #         ('expense_manager_id', '=', user.id),
        #         '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id),
        #     ]

        return res

    def read(self, fields):
        self.clear_caches()
        return super(HrExpense, self).read(fields)

class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'To Approve'),
        ('approve', 'Approved'),
        ('post', 'Posted'),
        ('done', 'Paid'),
        ('cancel', 'Refused')
    ], string='Status', index=True, readonly=True, tracking=True, copy=False, default='draft', required=True,
        help='Expense Report State')
    approver_ids = fields.One2many('hr.expense.approver', 'sheet_id', string="Approvers")
    user_status = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'To Approve'),
        ('approve', 'Approved'),
        ('post', 'Posted'),
        ('done', 'Paid'),
        ('cancel', 'Refused')], compute="_compute_user_status")

    expense_individual_approval = fields.Boolean(string='Expense Individual Approval',
                                            related='company_id.expense_individual_approval')

    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        for sheet in self:
            sheet.user_status = sheet.approver_ids.filtered(lambda approver: approver.user_id == self.env.user).status

    def get_approver(self):
        approver = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'draft')
        if len(approver) > 1:
            return approver[0]
        else:
            return approver

    def request_approval(self,approver):
        approver._create_activity()
        approver.write({'status': 'submit'})


    def action_approval_submit(self):
        # one by one request approval
        if self.get_approver():
            self.request_approval(self.get_approver())
            self.write({'state': 'submit'})
        else:
            raise UserError(_("You have to add at least one approver to submit your expense request."))

    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'hr.expense.sheet'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('sme_expense_approval.mail_activity_data_expense_approval').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities


    def approve_approval_expense_sheets(self,approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        if approver:
            approver.write({'status': 'approve'})
            self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()

            # one by one request approval
            next_approver = self.get_approver()
            if next_approver:
                self.request_approval(next_approver)

            status_lst = self.mapped('approver_ids.status')
            approvers = len(status_lst)
            result = {}
            if status_lst.count('approve') == approvers:
                responsible_id = self.user_id.id or self.env.user.id
                self.write({'state': 'approve', 'user_id': responsible_id})
            return result


    def refuse_sheet(self, reason,approver= None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        if approver:
            approver.write({'status': 'cancel'})
            self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
            # status_lst = self.mapped('approver_ids.status')
            # approvers = len(status_lst)
            # if status_lst.count('cancel') == approvers:
            self.write({'state': 'cancel'})

        else:
            if not self.user_has_groups('hr_expense.group_hr_expense_team_approver'):
                raise UserError(_("Only Managers and HR Officers can approve expenses"))
            elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
                current_managers = self.employee_id.expense_manager_id | self.employee_id.parent_id.user_id | self.employee_id.department_id.manager_id.user_id
                if self.employee_id.user_id == self.env.user:
                    raise UserError(_("You cannot refuse your own expenses"))
                if not self.env.user in current_managers and not self.user_has_groups('hr_expense.group_hr_expense_user') and self.employee_id.expense_manager_id != self.env.user:
                    raise UserError(_("You can only refuse your department expenses"))
            self.write({'state': 'cancel'})
            self.activity_update()

        for sheet in self:
            sheet.message_post_with_view('hr_expense.hr_expense_template_refuse_reason',
                                         values={'reason': reason, 'is_sheet': True, 'name': self.name})

    def reset_expense_sheets(self):
        result = super(HrExpenseSheet, self).reset_expense_sheets()
        if self.approver_ids:
            self.approver_ids.write({'status':'draft'})
            self.activity_unlink(['sme_expense_approval.mail_activity_data_expense_approval'])

        return result

    def read(self, fields):
        self.clear_caches()
        return super(HrExpenseSheet, self).read(fields)



class HrExpenseApprover(models.Model):
    _name = 'hr.expense.approver'
    _description = 'Expense Approver'

    user_id = fields.Many2one('res.users', string="User", required=True)
    name = fields.Char(related='user_id.name')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'To Approve'),
        ('approve', 'Approved'),
        ('post', 'Posted'),
        ('done', 'Paid'),
        ('cancel', 'Refused')
    ], string="Status", default="draft", readonly=True)
    sheet_id = fields.Many2one('hr.expense.sheet', string="Expense Sheet", ondelete='cascade')

    def button_approve(self):
        self.sheet_id.button_approve(self)

    def action_refuse(self):
        self.sheet_id.action_refuse(self)

    def action_create_activity(self):
        self.write({'status': 'submit'})
        self._create_activity()

    def _create_activity(self):
        for approver in self:
            approver.sheet_id.activity_schedule(
                'sme_expense_approval.mail_activity_data_expense_approval',
                user_id=approver.user_id.id)

    @api.onchange('user_id')
    def _onchange_approver_ids(self):
        return {'domain': {'user_id': [
            ('id', 'not in', self.sheet_id.approver_ids.mapped('user_id').ids + self.env.user.ids )]}}
