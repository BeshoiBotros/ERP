# -*- encoding: utf-8 -*-
{
    'name': 'Advanced Discount Manager',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Manage annual, quarterly, semi-annual, and per-invoice discounts with vendor distribution.',
    'description': """
        Advanced Discount Manager
        =========================
        Handles multi-tier discounts (annual, quarterly, semi-annual, per-invoice)
        and distributes the discount burden between the company and vendors based on
        vendor sales volume. The module creates independent journal entries without
        modifying the original invoices.
    """,
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au',
    'depends': ['account'],
    'data': [
        'security/eh_security.xml',
        'security/ir.model.access.csv',
        'data/discount_data.xml',
        'wizards/compute_discount_wizard_views.xml',
        'wizards/purge_discount_wizard_views.xml',
        'views/discount_type_views.xml',
        'views/discount_program_views.xml',
        'views/discount_entry_views.xml',
        'views/discount_dashboard_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'eh_discount_manager/static/src/css/discount_dashboard.css',
            'eh_discount_manager/static/src/js/discount_dashboard.js',
            'eh_discount_manager/static/src/js/discount_dashboard.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
