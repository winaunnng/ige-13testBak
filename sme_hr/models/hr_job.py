# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Job(models.Model):
    _inherit = "hr.job"

    applicant_id = fields.Many2one('hr.applicant', "Hired Applicant", tracking=True)


    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, department_id,x_studio_job_acquisition_approved_date)', 'The name of the job position must be unique per department in company!'),
    ]

    def action_reset_applicant(self):
        if self.applicant_id:
            self.applicant_id = False


