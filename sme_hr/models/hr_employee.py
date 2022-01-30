# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"
    coming_birthday = fields.Date('Coming Birthday')


class HrEmployeePrivate(models.Model):
    """
    NB: Any field only available on the model hr.employee (i.e. not on the
    hr.employee.public model) should have `groups="hr.group_hr_user"` on its
    definition to avoid being prefetched when the user hasn't access to the
    hr.employee model. Indeed, the prefetch loads the data for all the fields
    that are available according to the group defined on them.
    """
    _inherit = "hr.employee"

    departure_reason = fields.Selection([
            ('terminated', 'Contract Termination'),
            ('fired', 'Dismissed'),
            ('resigned', 'Resigned'),
            ('retired', 'Retired'),
            ('transfer', 'Transfer'),
            ('retrenched', 'Retrenched')
        ], string="Separation Reason", groups="hr.group_hr_user", copy=False, tracking=True)

    age = fields.Integer(string="Age", readonly=True, compute="_compute_age")
    coming_birthday = fields.Date('Coming Birthday',compute="_compute_coming_birthday")
    certificate = fields.Selection([
        ('bachelor', 'Bachelor'),
        ('doctorote', 'Doctorote'),
        ('master', 'Master'),
        ('secondary', 'Secondary'),
        ('diploma', 'Diploma'),
        ('under-graduate', 'Under Graduate'),
        ('other', 'Other'),
    ], 'Certificate Level', default='other', groups="hr.group_hr_user", tracking=True)
    warning_line_ids = fields.One2many('hr.warning.line', 'employee_id', string="Warnings")
    warning_expired_date = fields.Date('Warning Expired Date')
    has_warning = fields.Boolean('Has Warning',default = False)

    @api.depends("birthday")
    def _compute_age(self):
        for record in self:
            age = 0
            if record.birthday:
                age = relativedelta(fields.Date.today(), record.birthday).years
            record.age = age


    @api.depends("birthday")
    def _compute_coming_birthday(self):
        for record in self:
            if record.birthday:
                age = relativedelta(fields.Date.today(), record.birthday).years
                coming_birthday = record.birthday + relativedelta(years=age+1)
                record.coming_birthday = coming_birthday


    @api.model
    def action_cron_clear_warning(self):
        warnings = self.env['hr.warning.line'].search([])
        days_expire = int(self.env['ir.config_parameter'].sudo().get_param('hr.warning_expire')) or 365
        for warning in warnings :
            if (fields.Date.today() - warning.date).days >= days_expire:
                self.env.cr.execute("delete from hr_warning_line where employee_id = %s and id = %s", (warning.employee_id.id,warning.id))
                warning.employee_id.write({"warning_expired_date":fields.Date.today(),'has_warning':True})

class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    warning_expired_date = fields.Date('Warning Expired Date')
    has_warning = fields.Boolean('Has Warning', default=False)

class Contract(models.Model):
    _inherit = 'hr.contract'

    employment_loyalty = fields.Float(string="Employment Loyalty", readonly=True, compute="_compute_employment_loyalty")
    service_period = fields.Char('Service')
    loyalty_range = fields.Selection([
        ('01-6m', 'Within 6M'),
        ('02-7m', '7M~1 Yr'),
        ('03-1y', '1~3 yr'),
        ('04-3y', '3-5 yr'),
        ('05-5y', '5-10 yr'),
        ('06-10y', 'Over 10 yr'),
    ], 'Loyalty Range', readonly=True, store=True, groups="hr.group_hr_user", compute="_compute_loyalty_range")


    @api.depends("date_start","date_end")
    def _compute_employment_loyalty(self):
        for record in self:
            employment_loyalty = 0
            today = fields.Date.today()
            if record.date_start:
                employment = relativedelta(record.date_end if record.date_end and record.date_end < today else today , record.date_start)
                record.employment_loyalty = employment.years +  ( employment.months / 12)
                record.service_period = str(employment.years) + " Years " + str(employment.months) + " Months " + str(employment.days) + " Days "


    @api.depends("employment_loyalty", )
    def _compute_loyalty_range(self):
        for record in self:
            if record.employment_loyalty:
                if record.employment_loyalty <= 0.5:
                    record.loyalty_range = '01-6m'
                elif 0.5 < record.employment_loyalty <= 1:
                    record.loyalty_range = '02-7m'
                elif 1 < record.employment_loyalty <= 3:
                    record.loyalty_range = '03-1y'
                elif 3 < record.employment_loyalty <= 5:
                    record.loyalty_range = '04-3y'
                elif 5 < record.employment_loyalty <= 10:
                    record.loyalty_range = '05-5y'
                else:
                    record.loyalty_range = '06-10y'

class HrContractEmployeeReport(models.Model):
    _inherit = "hr.contract.employee.report"

    departure_reason = fields.Selection([
        ('terminated', 'Contract Termination'),
        ('fired', 'Dismissed'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired'),
        ('transfer', 'Transfer'),
        ('retrenched', 'Retrenched')
    ], string="Departure Reason", readonly=True)




class HrWarningLine(models.Model):
    _name = 'hr.warning.line'
    _description = "Warning of an employee"
    _order = 'date desc, id desc'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    date = fields.Date(required=True,default=fields.Date.context_today)
    description = fields.Text(string="Description")
    type = fields.Selection([('01', 'First Warning'),('02', 'Second Warning'),('03', 'Third Warning')], string="Type", default='01')
    lock = fields.Boolean('Lock', default=False)

    def unlink(self):
        for warn in self:
            if warn.lock == True:
                raise UserError(_('You are not allowed to delete lock-warnings !'))
        return super(HrWarningLine, self).unlink()



    def action_lock(self):
        for warn in self:
            warn.write({'lock':True})