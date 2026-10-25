# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""
PDF summary of a period, printed from the dashboard with its filters.

The report has no records of its own: the filters arrive as report data
and the figures are exactly the dashboard's (get_dashboard_data), so the
PDF can never disagree with the screen it was printed from.
"""

from odoo import api, fields, models

FILTER_KEYS = ('period', 'date_from', 'date_to', 'tag_id', 'include_draft')


class ReportPeriodSummary(models.AbstractModel):
    _name = 'report.eh_daily_disbursement.report_period_summary'
    _description = "Daily Disbursement Period Summary"

    @api.model
    def _get_report_values(self, docids, data=None):
        filters = {key: (data or {}).get(key) for key in FILTER_KEYS if (data or {}).get(key) is not None}
        dashboard = self.env['eh.daily.disbursement.dashboard'].get_dashboard_data(**filters)
        tag_id = filters.get('tag_id')
        return {
            'doc_ids': docids,
            'doc_model': 'eh.daily.disbursement',
            'docs': self.env['eh.daily.disbursement'].browse(docids),
            'company': self.env.company,
            'currency': self.env['res.currency'].browse(dashboard['currency']['id']),
            'tag': self.env['eh.daily.disbursement.tag'].browse(int(tag_id)) if tag_id else False,
            'include_draft': filters.get('include_draft', True),
            'data': dashboard,
            'to_date': fields.Date.to_date,
        }
