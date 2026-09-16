# -*- encoding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
from datetime import date


class EhDiscountDashboard(http.Controller):

    @http.route('/eh_discount_manager/dashboard_data', type='json', auth='user')
    def get_dashboard_data(self, date_from=None, date_to=None, vendor_id=None, **kwargs):
        """Return aggregated discount data for the dashboard."""
        domain = [('state', '=', 'posted')]

        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        entries = request.env['eh.discount.entry'].search(domain)

        # --- Vendor breakdown ---
        vl_domain = [('entry_id', 'in', entries.ids)]
        if vendor_id:
            vl_domain.append(('partner_id', '=', int(vendor_id)))

        vendor_lines = request.env['eh.discount.vendor.line'].search(vl_domain)

        vendor_map = {}
        for vl in vendor_lines:
            vid = vl.partner_id.id
            if vid not in vendor_map:
                vendor_map[vid] = {
                    'vendor_name': vl.partner_id.name,
                    'total_invoiced': 0.0,
                    'total_discount': 0.0,
                }
            vendor_map[vid]['total_invoiced'] += vl.invoiced_amount
            vendor_map[vid]['total_discount'] += vl.discount_amount

        vendor_rows = sorted(vendor_map.values(), key=lambda v: v['total_discount'], reverse=True)

        # --- KPI Summary (recalculated if vendor filter is active) ---
        if vendor_id:
            # When filtered by vendor, show only that vendor's share
            filtered_entry_ids = set(vendor_lines.mapped('entry_id').ids)
            filtered_entries = entries.filtered(lambda e: e.id in filtered_entry_ids)
            total_discount = sum(filtered_entries.mapped('total_discount'))
            company_share = sum(filtered_entries.mapped('company_discount'))
            vendor_share = sum(vl.discount_amount for vl in vendor_lines)
            program_count = len(filtered_entries.mapped('program_id'))
        else:
            total_discount = sum(entries.mapped('total_discount'))
            company_share = sum(entries.mapped('company_discount'))
            vendor_share = sum(entries.mapped('vendor_total_discount'))
            program_count = len(entries.mapped('program_id'))

        # --- Customer breakdown ---
        active_entries = entries if not vendor_id else entries.filtered(lambda e: e.id in set(vendor_lines.mapped('entry_id').ids))
        customer_map = {}
        for entry in active_entries:
            cid = entry.customer_id.id
            if cid not in customer_map:
                customer_map[cid] = {
                    'customer_name': entry.customer_id.name,
                    'entry_count': 0,
                    'total_discount': 0.0,
                }
            customer_map[cid]['entry_count'] += 1
            customer_map[cid]['total_discount'] += entry.total_discount

        customer_rows = sorted(customer_map.values(), key=lambda c: c['total_discount'], reverse=True)

        # --- All vendors for dropdown ---
        all_vl = request.env['eh.discount.vendor.line'].search([
            ('entry_id', 'in', entries.ids),
        ])
        vendors_list = []
        seen = set()
        for vl in all_vl:
            if vl.partner_id.id not in seen:
                seen.add(vl.partner_id.id)
                vendors_list.append({'id': vl.partner_id.id, 'name': vl.partner_id.name})
        vendors_list.sort(key=lambda v: v['name'] or '')

        currency = request.env.company.currency_id

        return {
            'kpi': {
                'total_discount': total_discount,
                'company_share': company_share,
                'vendor_share': vendor_share,
                'program_count': program_count,
            },
            'vendors': vendor_rows,
            'customers': customer_rows,
            'vendors_list': vendors_list,
            'currency_symbol': currency.symbol or '',
            'currency_position': currency.position or 'after',
        }
