# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Daily Disbursement',
    'summary': 'Track daily product disbursements and returns per company and category tag, with net cost totals.',
    'description': """Daily Disbursement Manager

One sheet per company, day and category tag records the products handed
out (disbursed) and the products brought back (returned) that day, at the
product cost captured when the line was entered. Each sheet totals the
disbursed, returned and net quantity and cost, and every line carries its
signed figures so period analysis is a single sum.

Built on the ERP Heritage accounting base: User / Manager privilege groups,
read-only access for the EH Auditor role, and multi-company isolation.
""",
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Inventory',
    'version': '17.0.1.0.0',
    'depends': ['eh_account_base', 'product', 'uom', 'mail'],
    'data': [
        'security/eh_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/mail_activity_data.xml',
        'data/ir_cron_data.xml',
        'wizards/import_lines_views.xml',
        'report/daily_disbursement_reports.xml',
        'views/daily_disbursement_tag_views.xml',
        'views/daily_disbursement_line_views.xml',
        'views/daily_disbursement_views.xml',
        'views/dashboard_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'eh_daily_disbursement/static/src/dashboard/dashboard.scss',
            'eh_daily_disbursement/static/src/dashboard/dashboard.js',
            'eh_daily_disbursement/static/src/dashboard/dashboard.xml',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
