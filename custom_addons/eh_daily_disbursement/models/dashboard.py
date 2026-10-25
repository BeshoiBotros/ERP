# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""
Data source of the daily disbursement dashboard.

One ORM-callable method, get_dashboard_data(), returns everything the OWL
dashboard renders. Calling it through the ORM (not a custom controller)
means the caller's access rights and company record rules apply to every
figure: a user only ever sees lines of the companies they selected.

All sums run in SQL via _read_group, grouped by currency as well, so a
selection spanning companies with different currencies is converted to
the current company's currency instead of adding EGP to USD.

Periods and their comparison window:
    today / yesterday     the day before
    this_week             week-to-date vs the same weekdays last week
    this_month            month-to-date vs the same days last month
    last_30_days          the 30 days before
    custom                the window of equal length just before
"""

from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..tools.xlsx_export import DisbursementWorkbook


PERIODS = ('today', 'yesterday', 'this_week', 'this_month', 'last_30_days', 'custom')
# Longer ranges switch the trend from daily to monthly buckets.
DAILY_TREND_MAX_DAYS = 92
MAX_CUSTOM_DAYS = 3 * 366
TOP_PRODUCTS = 10
TABLE_ROW_LIMIT = 500
RECENT_LINES = 10


class EhDailyDisbursementDashboard(models.AbstractModel):
    _name = 'eh.daily.disbursement.dashboard'
    _description = "Daily Disbursement Dashboard"

    @api.model
    def get_dashboard_data(self, period='this_month', date_from=None, date_to=None,
                           tag_id=None, include_draft=True):
        scope = self._scope(period, date_from, date_to, tag_id, include_draft)
        current, convert = scope['current'], scope['convert']
        now = self._totals(current, convert)
        before = self._totals(scope['previous'], convert)
        products = self._products(current, convert)
        currency = scope['currency']

        return {
            'period': {
                'key': period,
                'date_from': fields.Date.to_string(scope['date_from']),
                'date_to': fields.Date.to_string(scope['date_to']),
                'prev_from': fields.Date.to_string(scope['prev_from']),
                'prev_to': fields.Date.to_string(scope['prev_to']),
            },
            'currency': {
                'id': currency.id,
                'symbol': currency.symbol,
                'position': currency.position,
                'decimal_places': currency.decimal_places,
            },
            'converted': self._is_multi_currency(current),
            'kpi': {
                key: {
                    'value': now[key],
                    'previous': before[key],
                    'delta_pct': self._delta_pct(now[key], before[key]),
                }
                for key in now
            },
            'trend': self._trend(current, scope['date_from'], scope['date_to'], convert),
            'top_products': products[:TOP_PRODUCTS],
            'tables': self._tables(products),
            'by_tag': self._by_tag(current, convert),
            'sheets': self._sheet_counts(
                scope['tag_domain'], scope['date_from'], scope['date_to'], scope['today']),
            'recent': self._recent(current),
            'tags': self.env['eh.daily.disbursement.tag'].search_read([], ['name', 'color']),
            'line_domain': current,
        }

    @api.model
    def _export_xlsx(self, period='this_month', date_from=None, date_to=None,
                     tag_id=None, include_draft=True):
        """Return (filename, xlsx bytes) for the same filters as the
        dashboard: summary, every day, every product, tags and lines."""
        data = self.get_dashboard_data(period, date_from, date_to, tag_id, include_draft)
        scope = self._scope(period, date_from, date_to, tag_id, include_draft)
        current, convert = scope['current'], scope['convert']
        Line = self.env['eh.daily.disbursement.line']
        lines = Line.search(current, order='date, sheet_id, sequence, id')
        state_labels = dict(Line._fields['state']._description_selection(self.env))
        type_labels = dict(Line._fields['move_type']._description_selection(self.env))
        workbook = DisbursementWorkbook(
            title=_("Daily Disbursement"),
            labels=self._export_labels(),
        ).build(
            data=data,
            filters={
                'tag': self.env['eh.daily.disbursement.tag'].browse(int(tag_id)).name if tag_id else _("All tags"),
                'include_draft': include_draft,
                'company': self.env.company.name,
            },
            days=self._trend(current, scope['date_from'], scope['date_to'], convert,
                             granularity='day')['points'],
            products=self._products(current, convert),
            lines=[{
                'date': line.date,
                'sheet': line.sheet_id.name,
                'state': state_labels[line.state],
                'tag': line.tag_id.name or '',
                'product': line.product_id.display_name,
                'move_type': type_labels[line.move_type],
                'qty': line.qty,
                'uom': line.uom_id.name or '',
                'unit_cost': line.unit_cost,
                'subtotal': line.subtotal,
                'signed_subtotal': line.signed_subtotal,
                'currency': line.currency_id.name or '',
                'company': line.company_id.name,
                'note': line.note or '',
            } for line in lines],
        )
        filename = 'daily_disbursement_%s_%s.xlsx' % (
            data['period']['date_from'], data['period']['date_to'])
        return filename, workbook

    @api.model
    def _scope(self, period, date_from, date_to, tag_id, include_draft):
        """Resolve filters into dates, domains and the currency converter."""
        today = fields.Date.context_today(self)
        date_from, date_to, prev_from, prev_to = self._resolve_period(
            period, date_from, date_to, today)
        states = ['confirmed', 'closed'] + (['draft'] if include_draft else [])
        tag_domain = [('tag_id', '=', int(tag_id))] if tag_id else []
        scope = [('state', 'in', states)] + tag_domain
        currency = self.env.company.currency_id
        return {
            'today': today,
            'date_from': date_from, 'date_to': date_to,
            'prev_from': prev_from, 'prev_to': prev_to,
            'tag_domain': tag_domain,
            'current': scope + self._date_domain(date_from, date_to),
            'previous': scope + self._date_domain(prev_from, prev_to),
            'currency': currency,
            'convert': self._converter(currency, min(date_to, today)),
        }

    @api.model
    def _export_labels(self):
        return {
            'summary': _("Summary"), 'by_day': _("By Day"), 'products': _("Products"),
            'by_tag': _("By Tag"), 'lines': _("Lines"),
            'period': _("Period"), 'compared_with': _("Compared with"),
            'tag': _("Category tag"), 'drafts': _("Drafts included"),
            'company': _("Company"), 'currency': _("Currency"),
            'converted': _("Amounts from other company currencies are converted at the period-end rate."),
            'yes': _("Yes"), 'no': _("No"),
            'metric': _("Metric"), 'value': _("Value"), 'previous': _("Previous period"), 'change': _("Change"),
            'disbursed_cost': _("Disbursed cost"), 'returned_cost': _("Returned cost"),
            'net_cost': _("Net cost"), 'disbursed_qty': _("Disbursed quantity"),
            'returned_qty': _("Returned quantity"), 'net_qty': _("Net quantity"),
            'product_count': _("Products"), 'sheet_count': _("Sheets"),
            'date': _("Date"), 'disbursed': _("Disbursed"), 'returned': _("Returned"), 'net': _("Net"),
            'total': _("Total"), 'product': _("Product"), 'uom': _("Unit"),
            'out_qty': _("Disbursed qty"), 'out_cost': _("Disbursed cost"),
            'return_qty': _("Returned qty"), 'return_cost': _("Returned cost"),
            'sheet': _("Sheet"), 'state': _("Status"), 'type': _("Type"), 'qty': _("Quantity"),
            'unit_cost': _("Unit cost"), 'subtotal': _("Subtotal"), 'signed_subtotal': _("Net amount"),
            'note': _("Note"),
        }

    # ------------------------------------------------------------------
    # Period handling
    # ------------------------------------------------------------------

    @api.model
    def _resolve_period(self, period, date_from, date_to, today):
        """Return (date_from, date_to, prev_from, prev_to) as dates."""
        if period not in PERIODS:
            raise UserError(_("Unknown dashboard period %r.", period))
        if period == 'today':
            start = end = today
        elif period == 'yesterday':
            start = end = today - timedelta(days=1)
        elif period == 'this_week':
            week_start = int(self.env['res.lang']._lang_get(
                self.env.user.lang or 'en_US').week_start or 1)
            start = today - timedelta(days=(today.isoweekday() - week_start) % 7)
            return start, today, start - timedelta(days=7), today - timedelta(days=7)
        elif period == 'this_month':
            start = today.replace(day=1)
            prev_start = start - relativedelta(months=1)
            # Same days last month, clamped: 31 Mar compares to 1-28/29 Feb.
            prev_end = min(today - relativedelta(months=1), start - timedelta(days=1))
            return start, today, prev_start, prev_end
        elif period == 'last_30_days':
            start, end = today - timedelta(days=29), today
        else:
            if not date_from or not date_to:
                raise UserError(_("A custom period needs both a start and an end date."))
            start, end = fields.Date.to_date(date_from), fields.Date.to_date(date_to)
            if start > end:
                raise UserError(_("The period starts after it ends."))
            if (end - start).days >= MAX_CUSTOM_DAYS:
                raise UserError(_("Choose a period of at most three years."))
        span = (end - start).days + 1
        return start, end, start - timedelta(days=span), start - timedelta(days=1)

    @staticmethod
    def _date_domain(date_from, date_to):
        return [('date', '>=', fields.Date.to_string(date_from)),
                ('date', '<=', fields.Date.to_string(date_to))]

    @staticmethod
    def _delta_pct(value, previous):
        if not previous:
            return None
        return round((value - previous) / abs(previous) * 100, 1)

    # ------------------------------------------------------------------
    # Currency
    # ------------------------------------------------------------------

    def _converter(self, target, date):
        company = self.env.company

        def convert(amount, currency):
            if not amount or not currency or currency == target:
                return amount
            return currency._convert(amount, target, company, date)
        return convert

    def _is_multi_currency(self, domain):
        groups = self.env['eh.daily.disbursement.line']._read_group(domain, ['currency_id'])
        return len(groups) > 1 or any(
            cur != self.env.company.currency_id for (cur,) in groups)

    # ------------------------------------------------------------------
    # Aggregates
    # ------------------------------------------------------------------

    def _totals(self, domain, convert):
        Line = self.env['eh.daily.disbursement.line']
        totals = dict.fromkeys(
            ('disbursed_cost', 'returned_cost', 'net_cost',
             'disbursed_qty', 'returned_qty', 'net_qty'), 0.0)
        for move_type, currency, qty, cost in Line._read_group(
                domain, ['move_type', 'currency_id'], ['qty:sum', 'subtotal:sum']):
            prefix = 'disbursed' if move_type == 'out' else 'returned'
            totals[prefix + '_qty'] += qty
            totals[prefix + '_cost'] += convert(cost, currency)
        totals['net_qty'] = totals['disbursed_qty'] - totals['returned_qty']
        totals['net_cost'] = totals['disbursed_cost'] - totals['returned_cost']
        [(products,)] = Line._read_group(domain, aggregates=['product_id:count_distinct'])
        [(sheets,)] = Line._read_group(domain, aggregates=['sheet_id:count_distinct'])
        totals['product_count'] = products
        totals['sheet_count'] = sheets
        return totals

    def _trend(self, domain, date_from, date_to, convert, granularity=None):
        if not granularity:
            granularity = 'month' if (date_to - date_from).days >= DAILY_TREND_MAX_DAYS else 'day'
        monthly = granularity == 'month'
        buckets, cursor = {}, date_from.replace(day=1) if monthly else date_from
        step = relativedelta(months=1) if monthly else timedelta(days=1)
        while cursor <= date_to:
            buckets[cursor] = {'date': fields.Date.to_string(cursor),
                               'disbursed': 0.0, 'returned': 0.0, 'net': 0.0}
            cursor += step
        for bucket, move_type, currency, cost in self.env['eh.daily.disbursement.line']._read_group(
                domain, ['date:' + granularity, 'move_type', 'currency_id'], ['subtotal:sum']):
            point = buckets[fields.Date.to_date(bucket)]
            amount = convert(cost, currency)
            point['disbursed' if move_type == 'out' else 'returned'] += amount
            point['net'] += amount if move_type == 'out' else -amount
        return {'granularity': granularity, 'points': list(buckets.values())}

    def _products(self, domain, convert):
        """Per-product totals, biggest disbursed cost first."""
        rows = {}
        for product, move_type, currency, qty, cost in self.env['eh.daily.disbursement.line']._read_group(
                domain, ['product_id', 'move_type', 'currency_id'], ['qty:sum', 'subtotal:sum']):
            row = rows.setdefault(product.id, {
                'product_id': product.id, 'name': product.display_name,
                'uom': product.uom_id.name,
                'out_qty': 0.0, 'out_cost': 0.0, 'return_qty': 0.0, 'return_cost': 0.0,
            })
            prefix = 'out' if move_type == 'out' else 'return'
            row[prefix + '_qty'] += qty
            row[prefix + '_cost'] += convert(cost, currency)
        for row in rows.values():
            row['net_qty'] = row['out_qty'] - row['return_qty']
            row['net_cost'] = row['out_cost'] - row['return_cost']
        return sorted(rows.values(), key=lambda r: (-r['out_cost'], -r['out_qty'], r['name']))

    def _tables(self, products):
        """Disbursed and returned product tables (average unit cost)."""
        tables = {}
        for key, prefix in (('disbursed', 'out'), ('returned', 'return')):
            rows = [{
                'product_id': p['product_id'], 'name': p['name'], 'uom': p['uom'],
                'qty': p[prefix + '_qty'],
                'avg_cost': p[prefix + '_cost'] / p[prefix + '_qty'],
                'subtotal': p[prefix + '_cost'],
            } for p in products if p[prefix + '_qty']]
            rows.sort(key=lambda r: (-r['subtotal'], r['name']))
            tables[key] = {'rows': rows[:TABLE_ROW_LIMIT],
                           'truncated': len(rows) > TABLE_ROW_LIMIT}
        return tables

    def _by_tag(self, domain, convert):
        rows = {}
        for tag, move_type, currency, cost in self.env['eh.daily.disbursement.line']._read_group(
                domain, ['tag_id', 'move_type', 'currency_id'], ['subtotal:sum']):
            row = rows.setdefault(tag.id, {
                'tag_id': tag.id or False,
                'name': tag.name or _('No tag'),
                'color': tag.color or 0,
                'disbursed_cost': 0.0, 'returned_cost': 0.0,
            })
            row['disbursed_cost' if move_type == 'out' else 'returned_cost'] += convert(cost, currency)
        for row in rows.values():
            row['net_cost'] = row['disbursed_cost'] - row['returned_cost']
        return sorted(rows.values(), key=lambda r: -r['disbursed_cost'])

    def _sheet_counts(self, tag_scope, date_from, date_to, today):
        """Sheets per state in the period, plus what needs action now
        (whatever the period): drafts whose day passed, sheets to close."""
        Sheet = self.env['eh.daily.disbursement']
        by_state = dict.fromkeys(('draft', 'confirmed', 'closed'), 0)
        for state, count in Sheet._read_group(
                tag_scope + [('state', '!=', 'cancelled')] + self._date_domain(date_from, date_to),
                ['state'], ['__count']):
            by_state[state] = count
        return {
            'by_state': by_state,
            'overdue_drafts': Sheet.search_count(
                tag_scope + [('state', '=', 'draft'), ('date', '<', fields.Date.to_string(today))]),
            'to_close': Sheet.search_count(tag_scope + [('state', '=', 'confirmed')]),
        }

    def _recent(self, domain):
        lines = self.env['eh.daily.disbursement.line'].search(
            domain, order='create_date desc, id desc', limit=RECENT_LINES)
        return [{
            'id': line.id,
            'date': fields.Date.to_string(line.date),
            'sheet_id': line.sheet_id.id,
            'sheet': line.sheet_id.name,
            'product': line.product_id.display_name,
            'move_type': line.move_type,
            'qty': line.qty,
            'uom': line.uom_id.name,
            'subtotal': line.subtotal,
        } for line in lines]
