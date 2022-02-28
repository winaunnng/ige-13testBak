# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID

class RecruitmentStage(models.Model):
    _inherit = "hr.recruitment.stage"

    is_offer_stage = fields.Boolean("Is Offer Stage?")


class Applicant(models.Model):
    _inherit = "hr.applicant"

    def _default_stage_id(self):
        if self._context.get('default_job_id'):
            return self.env['hr.recruitment.stage'].search([
                '|',
                ('job_ids', '=', False),
                ('job_ids', '=', self._context['default_job_id']),
                ('fold', '=', False)
            ], order='sequence asc', limit=1).id
        return False

    stage_id = fields.Many2one('hr.recruitment.stage', 'Stage', ondelete='restrict', tracking=True,
                               domain="['|', ('job_ids', '=', False), ('job_ids', '=', job_id)]",
                               copy=False, index=True,
                               group_expand='_read_group_stage_ids',
                               default=_default_stage_id)
    is_offer_stage = fields.Boolean(related='stage_id.is_offer_stage',string="Is Offer Stage?")

    def _find_mail_template(self):
        return  self.env['ir.model.data'].xmlid_to_res_id('sme_hr.email_template_data_applicant_offer_letter', raise_if_not_found=False)

    def action_offer_email_send(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        template_id = self._find_mail_template()
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_template(template.lang, 'hr.applicant', self.ids[0])
        ctx = {
            'default_model': 'hr.applicant',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
