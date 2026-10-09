# -*- encoding: utf-8 -*-
{
    'name': 'Monthly Disbursement',
    'version': '17.0.1.0.6',
    'category': 'Inventory/Inventory',
    'summary': 'Track monthly product disbursements and returns (internal tool).',
    'description': """
        Monthly Disbursement Manager
        ============================
        An internal tool to track product disbursements and returns on a monthly basis.
        Allows filtering by product category tags (e.g. Perfumes, Nail Polish) and calculates net costs.
    """,
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au',
    'depends': ['base', 'product', 'uom', 'account'],
    'data': [
        'security/eh_security.xml',
        'security/ir.model.access.csv',
        'data/disbursement_data.xml',
        'views/product_category_tag_views.xml',
        'views/monthly_disbursement_views.xml',
        'views/disbursement_dashboard_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'eh_monthly_disbursement/static/src/css/disbursement_dashboard.css',
            'eh_monthly_disbursement/static/src/js/disbursement_dashboard.js',
            'eh_monthly_disbursement/static/src/xml/disbursement_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
