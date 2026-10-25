# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Dashboard data source: periods, figures, filters, currency, access."""

import json
from datetime import date

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged

from .common import EhDailyDisbursementCase


@tagged('post_install', '-at_install', 'eh_daily_disbursement')
class TestDashboardPeriods(EhDailyDisbursementCase):

    def _resolve(self, period, today, date_from=None, date_to=None):
        return self.env['eh.daily.disbursement.dashboard']._resolve_period(
            period, date_from, date_to, today)

    def test_presets(self):
        sunday = date(2026, 10, 25)
        self.assertEqual(self._resolve('today', sunday),
                         (sunday, sunday, date(2026, 10, 24), date(2026, 10, 24)))
        self.assertEqual(self._resolve('yesterday', sunday),
                         (date(2026, 10, 24),) * 2 + (date(2026, 10, 23),) * 2)
        self.assertEqual(self._resolve('this_month', sunday),
                         (date(2026, 10, 1), sunday, date(2026, 9, 1), date(2026, 9, 25)))
        self.assertEqual(self._resolve('last_30_days', sunday),
                         (date(2026, 9, 26), sunday, date(2026, 8, 27), date(2026, 9, 25)))
        self.assertEqual(self._resolve('custom', sunday, '2026-10-10', '2026-10-12'),
                         (date(2026, 10, 10), date(2026, 10, 12), date(2026, 10, 7), date(2026, 10, 9)))

    def test_week_follows_language_week_start(self):
        sunday = date(2026, 10, 25)
        lang = self.env['res.lang']._lang_get(self.env.user.lang or 'en_US')
        lang.week_start = '1'   # Monday
        self.assertEqual(self._resolve('this_week', sunday),
                         (date(2026, 10, 19), sunday, date(2026, 10, 12), date(2026, 10, 18)))
        lang.week_start = '6'   # Saturday, common in Egypt
        self.assertEqual(self._resolve('this_week', sunday)[:2], (date(2026, 10, 24), sunday))

    def test_month_comparison_clamps_short_months(self):
        self.assertEqual(self._resolve('this_month', date(2026, 3, 31))[2:],
                         (date(2026, 2, 1), date(2026, 2, 28)))

    def test_invalid_periods(self):
        today = date(2026, 10, 25)
        for args in (('fortnight',), ('custom',), ('custom', '2026-10-12', '2026-10-10'),
                     ('custom', '2020-01-01', '2026-01-01')):
            with self.assertRaises(UserError):
                self._resolve(args[0], today, *args[1:])


@tagged('post_install', '-at_install', 'eh_daily_disbursement')
class TestDashboardData(EhDailyDisbursementCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tag_nail = cls.env['eh.daily.disbursement.tag'].create(
            {'name': 'Nails', 'code': 'nails', 'color': 3})
        # Current window 2026-08-10..12, previous window 2026-08-07..09.
        cls.day1 = cls._create_sheet(
            [('out', cls.product_a, 3), ('out', cls.product_b, 4), ('return', cls.product_a, 1)],
            date=date(2026, 8, 10))                                  # +30 +20 -10
        cls.day1.action_confirm()
        cls.day3 = cls._create_sheet(
            [('out', cls.product_b, 2)], date=date(2026, 8, 12))      # +10, draft
        cls.nails = cls._create_sheet(
            [('out', cls.product_a, 1)], date=date(2026, 8, 11), tag_id=cls.tag_nail.id)  # +10
        cls.earlier = cls._create_sheet(
            [('out', cls.product_a, 2)], date=date(2026, 8, 8))       # previous: +20
        cls.earlier.action_confirm()
        cancelled = cls._create_sheet([('out', cls.product_a, 50)], date=date(2026, 8, 11))
        cancelled.action_cancel()

    def _data(self, **kwargs):
        kwargs.setdefault('period', 'custom')
        kwargs.setdefault('date_from', '2026-08-10')
        kwargs.setdefault('date_to', '2026-08-12')
        return self.env['eh.daily.disbursement.dashboard'].get_dashboard_data(**kwargs)

    def test_kpis_and_comparison(self):
        kpi = self._data()['kpi']
        self.assertEqual(kpi['disbursed_cost']['value'], 70)
        self.assertEqual(kpi['returned_cost']['value'], 10)
        self.assertEqual(kpi['net_cost']['value'], 60)
        self.assertEqual(kpi['net_qty']['value'], 9)
        self.assertEqual(kpi['net_cost']['previous'], 20)
        self.assertEqual(kpi['net_cost']['delta_pct'], 200.0)
        self.assertEqual(kpi['product_count']['value'], 2)
        self.assertEqual(kpi['sheet_count']['value'], 3)

    def test_no_previous_figures_gives_no_delta(self):
        kpi = self._data(date_from='2026-08-08', date_to='2026-08-08')['kpi']
        self.assertEqual(kpi['net_cost']['value'], 20)
        self.assertIsNone(kpi['net_cost']['delta_pct'])

    def test_draft_and_tag_filters(self):
        self.assertEqual(self._data(include_draft=False)['kpi']['net_cost']['value'], 40)
        self.assertEqual(self._data(tag_id=self.tag_nail.id)['kpi']['net_cost']['value'], 10)

    def test_trend_fills_every_day(self):
        trend = self._data()['trend']
        self.assertEqual(trend['granularity'], 'day')
        self.assertEqual(trend['points'], [
            {'date': '2026-08-10', 'disbursed': 50.0, 'returned': 10.0, 'net': 40.0},
            {'date': '2026-08-11', 'disbursed': 10.0, 'returned': 0.0, 'net': 10.0},
            {'date': '2026-08-12', 'disbursed': 10.0, 'returned': 0.0, 'net': 10.0},
        ])

    def test_long_range_trend_is_monthly(self):
        trend = self._data(date_from='2026-06-01', date_to='2026-09-30')['trend']
        self.assertEqual(trend['granularity'], 'month')
        self.assertEqual([p['date'] for p in trend['points']],
                         ['2026-06-01', '2026-07-01', '2026-08-01', '2026-09-01'])
        self.assertEqual(trend['points'][2]['net'], 80)

    def test_products_and_tables(self):
        data = self._data()
        top = data['top_products']
        # A: 30 + 10 disbursed, 10 returned; B: 20 + 10 disbursed.
        self.assertEqual([p['product_id'] for p in top], [self.product_a.id, self.product_b.id])
        self.assertEqual((top[0]['out_qty'], top[0]['out_cost']), (4, 40))
        self.assertEqual((top[0]['net_qty'], top[0]['net_cost']), (3, 30))
        self.assertEqual((top[1]['out_qty'], top[1]['out_cost']), (6, 30))
        disbursed = data['tables']['disbursed']['rows']
        self.assertEqual([(r['name'], r['qty'], r['avg_cost']) for r in disbursed],
                         [(self.product_a.display_name, 4, 10), (self.product_b.display_name, 6, 5)])
        returned = data['tables']['returned']['rows']
        self.assertEqual([(r['product_id'], r['subtotal']) for r in returned], [(self.product_a.id, 10)])
        self.assertFalse(data['tables']['disbursed']['truncated'])

    def test_by_tag(self):
        by_tag = {row['name']: row for row in self._data()['by_tag']}
        self.assertEqual(by_tag['Perfumes']['net_cost'], 50)
        self.assertEqual((by_tag['Nails']['net_cost'], by_tag['Nails']['color']), (10, 3))

    def test_sheet_counts_and_recent(self):
        data = self._data()
        self.assertEqual(data['sheets']['by_state'], {'draft': 2, 'confirmed': 1, 'closed': 0})
        # day3 and nails are drafts whose day has passed (2026-08 < today).
        self.assertEqual(data['sheets']['overdue_drafts'], 2)
        self.assertEqual(data['sheets']['to_close'], 2)
        self.assertEqual(len(data['recent']), 5)
        self.assertEqual({r['sheet'] for r in data['recent']},
                         {self.day1.name, self.day3.name, self.nails.name})

    def test_payload_is_json_and_domain_reusable(self):
        data = self._data()
        json.dumps(data)
        lines = self.env['eh.daily.disbursement.line'].search(data['line_domain'])
        self.assertEqual(sum(lines.mapped('signed_subtotal')), data['kpi']['net_cost']['value'])
        self.assertFalse(data['converted'])
        self.assertEqual(data['currency']['id'], self.env.company.currency_id.id)

    def test_preset_period_runs(self):
        data = self._data(period='this_month', date_from=None, date_to=None)
        today = fields.Date.context_today(self.env['eh.daily.disbursement'])
        self.assertEqual(data['period']['date_to'], fields.Date.to_string(today))

    def test_requires_access(self):
        outsider = new_test_user(self.env, login='dd_outsider', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.env['eh.daily.disbursement.dashboard'].with_user(outsider).get_dashboard_data()
        data = self.env['eh.daily.disbursement.dashboard'].with_user(self.auditor).get_dashboard_data(
            period='custom', date_from='2026-08-10', date_to='2026-08-12')
        self.assertEqual(data['kpi']['net_cost']['value'], 60)


@tagged('post_install', '-at_install', 'eh_daily_disbursement')
class TestDashboardCompanies(EhDailyDisbursementCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main = cls.env.company
        eur = cls.env.ref('base.EUR')
        eur.active = True
        if eur == cls.main.currency_id:
            eur = cls.env.ref('base.USD')
            eur.active = True
        cls.foreign_currency = eur
        cls.foreign = cls.env['res.company'].create({
            'name': 'Foreign Co', 'currency_id': eur.id})
        # 1 main-currency unit = 0.5 foreign: 10 foreign = 20 main.
        cls.env['res.currency.rate'].create({
            'currency_id': eur.id, 'name': '2026-01-01', 'rate': 0.5,
            'company_id': cls.main.id})
        cls.user.write({'company_ids': [(4, cls.foreign.id)]})
        cls._create_sheet([('out', cls.product_a, 1)], date=date(2026, 8, 10))  # 10 main
        cls.env['eh.daily.disbursement'].with_company(cls.foreign).create({
            'date': date(2026, 8, 10), 'company_id': cls.foreign.id, 'tag_id': cls.tag.id,
            'line_ids': [(0, 0, {'product_id': cls.product_a.id, 'qty': 1, 'unit_cost': 10})],
        })                                                                       # 10 foreign

    def _data(self, companies):
        return self.env['eh.daily.disbursement.dashboard'].with_user(self.user).with_context(
            allowed_company_ids=companies.ids,
        ).get_dashboard_data(period='custom', date_from='2026-08-10', date_to='2026-08-10')

    def test_only_selected_companies_count(self):
        data = self._data(self.main)
        self.assertEqual(data['kpi']['net_cost']['value'], 10)
        self.assertFalse(data['converted'])

    def test_mixed_currencies_are_converted(self):
        data = self._data(self.main | self.foreign)
        self.assertTrue(data['converted'])
        self.assertAlmostEqual(data['kpi']['net_cost']['value'], 30)
        self.assertAlmostEqual(data['trend']['points'][0]['net'], 30)
        self.assertEqual(data['currency']['id'], self.main.currency_id.id)
