# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""
XLSX download of the dashboard's current view.

Streamed straight to the browser instead of being stored as an
ir.attachment first, so repeated exports leave nothing behind in the
database. Figures are computed as the logged-in user (request.env), so
access rights and company rules apply exactly as on the dashboard.
"""

from odoo import http
from odoo.http import content_disposition, request

XLSX_MIMETYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class DailyDisbursementExport(http.Controller):

    # Read-only (no state change), so CSRF protection buys nothing here and
    # GET keeps the URL usable from a plain link.
    @http.route('/eh_daily_disbursement/export/xlsx', type='http', auth='user',
                methods=['GET', 'POST'], csrf=False)
    def export_xlsx(self, period='this_month', date_from=None, date_to=None,
                    tag_id=None, include_draft='1', **kwargs):
        filename, content = request.env['eh.daily.disbursement.dashboard']._export_xlsx(
            period=period,
            date_from=date_from or None,
            date_to=date_to or None,
            tag_id=int(tag_id) if tag_id else None,
            include_draft=include_draft not in ('0', 'false', 'False', ''),
        )
        return request.make_response(content, headers=[
            ('Content-Type', XLSX_MIMETYPE),
            ('Content-Disposition', content_disposition(filename)),
        ])
