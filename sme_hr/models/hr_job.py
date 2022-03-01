# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Job(models.Model):
    _inherit = "hr.job"

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, department_id,x_studio_job_acquisition_approved_date)', 'The name of the job position must be unique per department in company!'),
    ]