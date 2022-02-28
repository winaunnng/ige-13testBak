# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, _lt, fields
from odoo.tools.misc import format_date


class report_account_aged_partner(models.AbstractModel):
    _inherit = "account.aged.partner"

    filter_accounts = True

    def _get_columns_name(self, options):
        columns = [
            {},
            {'name': _("Partner"), 'class': 'date', 'style': 'white-space:nowrap;'},
            {'name': _("Reference"), 'class': 'date', 'style': 'white-space:nowrap;'},
            {'name': _("Due Date"), 'class': 'date', 'style': 'white-space:nowrap;'},
            {'name': _("Journal"), 'class': '', 'style': 'text-align:center; white-space:nowrap;'},
            {'name': _("Account"), 'class': '', 'style': 'text-align:center; white-space:nowrap;'},
            {'name': _("Exp. Date"), 'class': 'date', 'style': 'white-space:nowrap;'},
            {'name': _("As of: %s") % format_date(self.env, options['date']['date_to']), 'class': 'number sortable',
             'style': 'white-space:nowrap;'},
            {'name': _("1 - 30"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("31 - 60"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("61 - 90"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("91 - 120"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("Older"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("Total"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
        ]
        return columns

    @api.model
    def _get_filter_accounts(self):
        domain =[]
        if self.env.context.get('model') == 'account.aged.receivable':
            domain.append('receivable')
        else:
            domain.append('payable')

        return self.env['account.account'].search([
            ('internal_type','in',domain),
            ('company_id', 'in', self.env.user.company_ids.ids or [self.env.company.id])
        ], order="company_id, name")

    @api.model
    def _get_filter_account_groups(self):
        accounts = self._get_filter_accounts()
        groups = self.env['account.group'].search([], order='code_prefix')
        ret = self.env['account.group']
        for account_group in groups:
            # Only display the group if it doesn't exclude every account
            if accounts - account_group.excluded_account_ids:
                ret += account_group
        return ret

    @api.model
    def _init_filter_accounts(self, options, previous_options=None):
        if self.filter_accounts is None:
            return

        previous_company = False
        if previous_options and previous_options.get('accounts'):
            account_map = dict((opt['id'], opt['selected']) for opt in previous_options['accounts'] if
                               opt['id'] != 'divider' and 'selected' in opt)
        else:
            account_map = {}
        options['accounts'] = []

        group_header_displayed = False
        default_group_ids = []
        # for group in self._get_filter_account_groups():
        #     account_ids = (self._get_filter_accounts() - group.excluded_account_ids).ids
        #     if len(account_ids):
        #         if not group_header_displayed:
        #             group_header_displayed = True
        #             options['accounts'].append({'id': 'divider', 'name': _('Journal Groups')})
        #             default_group_ids = account_ids
        #         options['accounts'].append({'id': 'group', 'name': group.name, 'ids': account_ids})

        for a in self._get_filter_accounts():
            if a.company_id != previous_company:
                options['accounts'].append({'id': 'divider', 'name': a.company_id.name})
                previous_company = a.company_id
            options['accounts'].append({
                'id': a.id,
                'name': a.name,
                'code': a.code,
                'type': a.internal_type,
                'selected': account_map.get(a.id, a.id in default_group_ids),
            })

    @api.model
    def _get_options_accounts(self, options):
        return [
            account for account in options.get('accounts', []) if
            not account['id'] in ('divider', 'group') and account['selected']
        ]

    @api.model
    def _get_options_accounts_domain(self, options):
        # Make sure to return an empty array when nothing selected to handle archived journals.
        selected_accounts = self._get_options_accounts(options)
        return selected_accounts and [('journal_id', 'in', [j['id'] for j in selected_accounts])] or []

    def _set_context(self, options):
        ctx = super(report_account_aged_partner, self)._set_context(options)
        if options.get('accounts'):
            ctx['account_ids'] = [j.get('id') for j in options.get('accounts') if j.get('selected')]

        return ctx

    def _get_templates(self):
        return {
                'main_template': 'account_reports.main_template',
                'main_table_header_template': 'account_reports.main_table_header',
                'line_template': 'account_reports.line_template',
                'footnotes_template': 'account_reports.footnotes_template',
                'search_template': 'sme_aging_account_filter(13).search_template_aging',
        }

    @api.model
    def _get_lines(self, options, line_id=None):
        sign = -1.0 if self.env.context.get('aged_balance') else 1.0
        lines = []
        account_types = [self.env.context.get('account_type')]
        context = {'include_nullified_amount': True}
        if line_id and 'partner_' in line_id:
            # we only want to fetch data about this partner because we are expanding a line
            partner_id_str = line_id.split('_')[1]
            if partner_id_str.isnumeric():
                partner_id = self.env['res.partner'].browse(int(partner_id_str))
            else:
                partner_id = False
            context.update(partner_ids=partner_id)
        results, total, amls = self.env['report.account.report_agedpartnerbalance'].with_context(
            **context)._get_partner_move_lines(account_types, self._context['date_to'], 'posted', 30)

        for values in results:
            vals = {
                'id': 'partner_%s' % (values['partner_id'],),
                'name': values['name'],
                'level': 2,
                'columns': [{'name': ''}] * 6 + [{'name': self.format_value(sign * v), 'no_format': sign * v}
                                                 for v in [values['direction'], values['4'],
                                                           values['3'], values['2'],
                                                           values['1'], values['0'], values['total']]],
                'trust': values['trust'],
                'unfoldable': True,
                'unfolded': 'partner_%s' % (values['partner_id'],) in options.get('unfolded_lines'),
                'partner_id': values['partner_id'],
            }
            lines.append(vals)
            if 'partner_%s' % (values['partner_id'],) in options.get('unfolded_lines'):
                for line in amls[values['partner_id']]:
                    aml = line['line']
                    if aml.move_id.is_purchase_document():
                        caret_type = 'account.invoice.in'
                    elif aml.move_id.is_sale_document():
                        caret_type = 'account.invoice.out'
                    elif aml.payment_id:
                        caret_type = 'account.payment'
                    else:
                        caret_type = 'account.move'

                    line_date = aml.date_maturity or aml.date
                    if not self._context.get('no_format'):
                        line_date = format_date(self.env, line_date)
                    vals = {
                        'id': aml.id,
                        'name': aml.move_id.name,
                        'class': 'date',
                        'caret_options': caret_type,
                        'level': 6,
                        'parent_id': 'partner_%s' % (values['partner_id'],),
                        'columns': [{'name': v} for v in
                                    [(aml.partner_id and aml.partner_id.name) or '',aml.move_id.ref or '', format_date(self.env, aml.date_maturity or aml.date), aml.journal_id.code,
                                     aml.account_id.display_name, format_date(self.env, aml.expected_pay_date)]] +
                                   [{'name': self.format_value(sign * v, blank_if_zero=True), 'no_format': sign * v} for
                                    v in [line['period'] == 6 - i and line['amount'] or 0 for i in range(7)]],
                        'action_context': {
                            'default_type': aml.move_id.type,
                            'default_journal_id': aml.move_id.journal_id.id,
                        },
                        'title_hover': self._format_aml_name(aml.name, aml.ref, aml.move_id.name),
                    }
                    lines.append(vals)
        if total and not line_id:
            total_line = {
                'id': 0,
                'name': _('Total'),
                'class': 'total',
                'level': 2,
                'columns': [{'name': ''}] * 6 + [{'name': self.format_value(sign * v), 'no_format': sign * v} for v in
                                                 [total[6], total[4], total[3], total[2], total[1], total[0],
                                                  total[5]]],
            }
            lines.append(total_line)
        return lines


def get_report_informations(self, options):

        options = self._get_options(options)
        info = super(report_account_aged_partner, self).get_report_informations(options)
        if options.get('accounts'):
            accounts_selected = set(account['id'] for account in options['accounts'] if account.get('selected'))
            # for account_group in self.env['account.group'].search([]):
            #     if accounts_selected and accounts_selected == set(self._get_filter_accounts().ids):
            #         options['name_account_group'] = account_group.name
            #         break

        report_manager = self._get_report_manager(options)
        searchview_dict = {'options': options, 'context': self.env.context}
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self._get_reports_buttons_in_sequence(),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view'].render_template(
                    self._get_templates().get('search_template', 'sme_aging_account_filter(13).search_template_aging'),
                    values=searchview_dict),
                }
        return info

class report_account_aged_receivable(models.AbstractModel):
    _inherit = "account.aged.receivable"


class report_account_aged_payable(models.AbstractModel):
    _inherit = "account.aged.payable"


