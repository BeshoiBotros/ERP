# -*- encoding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import http, _
# pyrefly: ignore [missing-import]
from odoo.http import request


class MonthlyDisbursementController(http.Controller):

    @http.route('/eh_monthly_disbursement/dashboard_data', type='json', auth='user')
    def get_dashboard_data(self, month=None, year=None, category_tag_id=None):
        domain = [('state', 'in', ['confirmed', 'done'])]
        
        if month:
            domain.append(('month', '=', str(month)))
        if year:
            domain.append(('year', '=', int(year)))
        if category_tag_id:
            domain.append(('category_tag_id', '=', int(category_tag_id)))
            
        disbursements = request.env['eh.monthly.disbursement'].search(domain)
        
        # Aggregate totals
        total_disbursed_cost = sum(disbursements.mapped('total_disbursed_cost'))
        total_returned_cost = sum(disbursements.mapped('total_returned_cost'))
        net_cost = sum(disbursements.mapped('net_cost'))
        
        total_disbursed_qty = sum(disbursements.mapped('total_disbursed_qty'))
        total_returned_qty = sum(disbursements.mapped('total_returned_qty'))
        net_qty = sum(disbursements.mapped('net_qty'))
        
        # Product Analysis (Top 10)
        product_data = {}
        for d in disbursements:
            for line in d.line_ids:
                pid = line.product_id.id
                pname = line.product_id.name
                
                if pid not in product_data:
                    product_data[pid] = {'name': pname, 'out_qty': 0, 'return_qty': 0}
                    
                if line.move_type == 'out':
                    product_data[pid]['out_qty'] += line.qty
                else:
                    product_data[pid]['return_qty'] += line.qty
                    
        # Sort by out_qty descending
        sorted_products = sorted(product_data.values(), key=lambda x: x['out_qty'], reverse=True)[:10]
        
        product_names = [p['name'] for p in sorted_products]
        product_out_qtys = [p['out_qty'] for p in sorted_products]
        product_return_qtys = [p['return_qty'] for p in sorted_products]
        
        # Category Analysis
        cat_data = {}
        for d in disbursements:
            cat_name = d.category_tag_id.name or _('Undefined')
            if cat_name not in cat_data:
                cat_data[cat_name] = 0
            cat_data[cat_name] += d.total_disbursed_cost
            
        # Recent Activity (Last 10 lines)
        lines = request.env['eh.monthly.disbursement.line'].search([
            ('disbursement_id', 'in', disbursements.ids)
        ], order='date desc, id desc', limit=10)
        
        recent_activity = []
        for line in lines:
            recent_activity.append({
                'date': line.date.strftime('%Y-%m-%d'),
                'product': line.product_id.name,
                'move_type': line.move_type,
                'qty': line.qty,
                'sign': '+' if line.move_type == 'out' else '-'
            })

        # Translated labels — Python _() always respects the user's language
        labels = {
            'title': _('Monthly Disbursement Dashboard'),
            'allMonths': _('All Months'),
            'allYears': _('All Years'),
            'allCategories': _('All Categories'),
            'disbursedOut': _('Disbursed (Out)'),
            'returnedIn': _('Returned (In)'),
            'netFinal': _('Net Final'),
            'productsCount': _('Products Count'),
            'uniqueProducts': _('Unique products moved'),
            'units': _('Units'),
            'netUnits': _('Net Units'),
            'topProducts': _('Top 10 Products by Quantity'),
            'costByCategory': _('Cost by Category'),
            'recentActivity': _('Recent Activity'),
            'noActivity': _('No recent activity found.'),
            'disbursed': _('Disbursed'),
            'returned': _('Returned'),
            'disbursedProductsOut': _('Disbursed Products (Out)'),
            'returnedProductsIn': _('Returned Products (In)'),
            'product': _('Product'),
            'qty': _('Qty'),
            'price': _('Price'),
            'totalCost': _('Total Cost'),
            'totalDisbursedCost': _('Total Disbursed Cost'),
            'totalReturnedCost': _('Total Returned Cost'),
            'monthsInvoice': _("Month's Invoice = Total Disbursed Cost - Total Returned Cost ="),
        }

        # Translated month names
        months = [
            {'value': 1, 'label': _('January')},
            {'value': 2, 'label': _('February')},
            {'value': 3, 'label': _('March')},
            {'value': 4, 'label': _('April')},
            {'value': 5, 'label': _('May')},
            {'value': 6, 'label': _('June')},
            {'value': 7, 'label': _('July')},
            {'value': 8, 'label': _('August')},
            {'value': 9, 'label': _('September')},
            {'value': 10, 'label': _('October')},
            {'value': 11, 'label': _('November')},
            {'value': 12, 'label': _('December')},
        ]

        # Tables Data
        disbursed_table_dict = {}
        returned_table_dict = {}
        
        for d in disbursements:
            for line in d.disbursement_line_ids:
                key = (line.product_id.id, line.purchase_price)
                if key not in disbursed_table_dict:
                    disbursed_table_dict[key] = {
                        'product_name': line.product_id.name,
                        'qty': 0.0,
                        'price': line.purchase_price,
                        'subtotal': 0.0,
                        'uom': line.uom_id.name or '',
                    }
                disbursed_table_dict[key]['qty'] += line.qty
                disbursed_table_dict[key]['subtotal'] += line.subtotal
                
            for line in d.return_line_ids:
                key = (line.product_id.id, line.purchase_price)
                if key not in returned_table_dict:
                    returned_table_dict[key] = {
                        'product_name': line.product_id.name,
                        'qty': 0.0,
                        'price': line.purchase_price,
                        'subtotal': 0.0,
                        'uom': line.uom_id.name or '',
                    }
                returned_table_dict[key]['qty'] += line.qty
                returned_table_dict[key]['subtotal'] += line.subtotal

        disbursed_table = list(disbursed_table_dict.values())
        returned_table = list(returned_table_dict.values())
        
        # Sort tables by subtotal descending
        disbursed_table.sort(key=lambda x: x['subtotal'], reverse=True)
        returned_table.sort(key=lambda x: x['subtotal'], reverse=True)

        return {
            'labels': labels,
            'months': months,
            'kpi': {
                'total_disbursed_cost': total_disbursed_cost,
                'total_returned_cost': total_returned_cost,
                'net_cost': net_cost,
                'total_disbursed_qty': total_disbursed_qty,
                'total_returned_qty': total_returned_qty,
                'net_qty': net_qty,
                'product_count': len(product_data),
            },
            'tables': {
                'disbursed': disbursed_table,
                'returned': returned_table,
            },
            'charts': {
                'products': {
                    'labels': product_names,
                    'out_data': product_out_qtys,
                    'return_data': product_return_qtys,
                },
                'categories': {
                    'labels': list(cat_data.keys()),
                    'data': list(cat_data.values()),
                }
            },
            'recent_activity': recent_activity
        }
