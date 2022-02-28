# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.tools.misc import format_date

from dateutil.relativedelta import relativedelta
from itertools import chain


class ReportAccountAgedPartner(models.AbstractModel):
    _inherit = "account.aged.partner"

    filter_accounts = True

    @api.model
    def _get_filter_accounts(self):
        domain = []
        if self.env.context.get('model') == 'account.aged.receivable':
            domain.append('receivable')
        else:
            domain.append('payable')

        return self.env['account.account'].search([
            ('internal_type', 'in', domain),
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
            account_map = dict((opt['id'], opt['selected']) for opt in previous_options['accounts'] if opt['id'] != 'divider' and 'selected' in opt)
        else:
            account_map = {}

        options['accounts'] = []
        default_group_ids = []
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

    def _get_templates(self):
        return {
            'main_template': 'account_reports.main_template',
            'main_table_header_template': 'account_reports.main_table_header',
            'line_template': 'account_reports.line_template',
            'footnotes_template': 'account_reports.footnotes_template',
            'search_template': 'sme_aging_account_filter.search_template',
            'line_caret_options': 'account_reports.line_caret_options',
        }

    @api.model
    def _get_sql(self):
        options = self.env.context['report_options']

        all_accounts = tuple(self.env['account.account'].search([('internal_type', '=', options['filter_account_type'])]).ids)
        if options.get('accounts'):
            accounts = (tuple(set(account['id'] for account in options['accounts'] if account.get('selected'))))
            if not accounts:
                accounts = all_accounts
        query = ("""
                SELECT
                    {move_line_fields},
                    account_move_line.amount_currency as amount_currency,
                    account_move_line.partner_id AS partner_id,
                    partner.name AS partner_name,
                    COALESCE(trust_property.value_text, 'normal') AS partner_trust,
                    COALESCE(account_move_line.currency_id, journal.currency_id) AS report_currency_id,
                    account_move_line.payment_id AS payment_id,
                    COALESCE(account_move_line.date_maturity, account_move_line.date) AS report_date,
                    account_move_line.expected_pay_date AS expected_pay_date,
                    move.move_type AS move_type,
                    move.name AS move_name,
                    move.ref AS move_ref,
                    account.code || ' ' || account.name AS account_name,
                    account.code AS account_code,""" + ','.join([("""
                    CASE WHEN period_table.period_index = {i}
                    THEN %(sign)s * ROUND((
                        account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0)
                    ) * currency_table.rate, currency_table.precision)
                    ELSE 0 END AS period{i}""").format(i=i) for i in range(6)]) + """
                FROM account_move_line
                JOIN account_move move ON account_move_line.move_id = move.id
                JOIN account_journal journal ON journal.id = account_move_line.journal_id
                JOIN account_account account ON account.id = account_move_line.account_id
                LEFT JOIN res_partner partner ON partner.id = account_move_line.partner_id
                LEFT JOIN ir_property trust_property ON (
                    trust_property.res_id = 'res.partner,'|| account_move_line.partner_id
                    AND trust_property.name = 'trust'
                    AND trust_property.company_id = account_move_line.company_id
                )
                JOIN {currency_table} ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN LATERAL (
                    SELECT part.amount, part.debit_move_id
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date)s
                ) part_debit ON part_debit.debit_move_id = account_move_line.id
                LEFT JOIN LATERAL (
                    SELECT part.amount, part.credit_move_id
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date)s
                ) part_credit ON part_credit.credit_move_id = account_move_line.id
                JOIN {period_table} ON (
                    period_table.date_start IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) <= DATE(period_table.date_start)
                )
                AND (
                    period_table.date_stop IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) >= DATE(period_table.date_stop)
                )
                WHERE account.internal_type = %(account_type)s
                AND account.id IN %(accounts)s 
                AND account.exclude_from_aged_reports IS NOT TRUE
                GROUP BY account_move_line.id, partner.id, trust_property.id, journal.id, move.id, account.id,
                         period_table.period_index, currency_table.rate, currency_table.precision
                HAVING ROUND(account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0), currency_table.precision) != 0
            """).format(
            move_line_fields=self._get_move_line_fields('account_move_line'),
            currency_table=self.env['res.currency']._get_query_currency_table(options),
            period_table=self._get_query_period_table(options),
        )

        params = {
            'account_type': options['filter_account_type'],
            'accounts': accounts,
            'sign': 1 if options['filter_account_type'] == 'receivable' else -1,
            'date': options['date']['date_to'],
        }

        return self.env.cr.mogrify(query, params).decode(self.env.cr.connection.encoding)



    def get_report_informations(self, options):
        '''
        return a dictionary of informations that will be needed by the js widget, manager_id, footnotes, html of report and searchview, ...
        '''
        options = self._get_options(options)
        info = super(ReportAccountAgedPartner, self).get_report_informations(options)
        searchview_dict = {'options': options, 'context': self.env.context}
        report_manager = self._get_report_manager(options)
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self._get_reports_buttons_in_sequence(options),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view']._render_template(
                    self._get_templates().get('search_template', 'sme_aging_account_filter.search_template'),
                    values=searchview_dict),
                }
        return info

