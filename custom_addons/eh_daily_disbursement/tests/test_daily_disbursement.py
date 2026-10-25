# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Data model tests: reference, cost snapshot, totals, line mirrors, ACLs."""

from datetime import date

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import EhDailyDisbursementCase


@tagged('post_install', '-at_install', 'eh_daily_disbursement')
class TestDailyDisbursement(EhDailyDisbursementCase):

    def test_reference_uses_sheet_date(self):
        sheet = self._create_sheet(date=date(2026, 1, 15))
        self.assertTrue(sheet.name.startswith('DD/2026/01/15/'), sheet.name)

    def test_unit_cost_defaults_to_product_cost(self):
        sheet = self._create_sheet([('out', self.product_a, 1)])
        self.assertEqual(sheet.line_ids.unit_cost, 10.0)

    def test_explicit_unit_cost_is_kept(self):
        sheet = self._create_sheet([('out', self.product_a, 1, 7.5)])
        self.assertEqual(sheet.line_ids.unit_cost, 7.5)

    def test_cost_snapshot_survives_product_cost_change(self):
        sheet = self._create_sheet([('out', self.product_a, 1)])
        self.product_a.standard_price = 99.0
        self.assertEqual(sheet.line_ids.unit_cost, 10.0)

    def test_totals_and_signed_figures(self):
        sheet = self._create_sheet([
            ('out', self.product_a, 3),     # 30
            ('out', self.product_b, 2),     # 10
            ('return', self.product_a, 1),  # 10
        ])
        self.assertEqual(sheet.disbursed_qty, 5)
        self.assertEqual(sheet.disbursed_cost, 40)
        self.assertEqual(sheet.returned_qty, 1)
        self.assertEqual(sheet.returned_cost, 10)
        self.assertEqual(sheet.net_qty, 4)
        self.assertEqual(sheet.net_cost, 30)
        self.assertEqual(sheet.line_count, 3)
        ret = sheet.line_ids.filtered(lambda l: l.move_type == 'return')
        self.assertEqual((ret.signed_qty, ret.signed_subtotal), (-1, -10))
        # Net over the lines is a plain sum of the signed figures.
        self.assertEqual(sum(sheet.line_ids.mapped('signed_subtotal')), sheet.net_cost)

    def test_totals_follow_line_edits(self):
        sheet = self._create_sheet([('out', self.product_a, 3)])
        sheet.line_ids.move_type = 'return'
        self.assertEqual((sheet.disbursed_cost, sheet.returned_cost, sheet.net_cost), (0, 30, -30))
        sheet.line_ids.qty = 1
        self.assertEqual(sheet.net_cost, -10)

    def test_line_mirrors_sheet_fields(self):
        sheet = self._create_sheet([('out', self.product_a, 1)], date=date(2026, 3, 1))
        line = sheet.line_ids
        self.assertEqual(line.date, date(2026, 3, 1))
        self.assertEqual(line.tag_id, self.tag)
        self.assertEqual(line.company_id, self.company)
        self.assertEqual(line.state, 'draft')
        sheet.date = date(2026, 3, 2)
        self.assertEqual(line.date, date(2026, 3, 2))

    def test_allowed_categories_follow_tag(self):
        sheet = self._create_sheet()
        self.assertEqual(sheet.allowed_categ_ids, self.categ_perfume)
        sheet.tag_id = False
        self.assertIn(self.categ_other, sheet.allowed_categ_ids)

    def test_copy_resets_date_and_reference(self):
        sheet = self._create_sheet([('out', self.product_a, 2)], date=date(2026, 2, 1))
        copy = sheet.copy()
        self.assertNotEqual(copy.name, sheet.name)
        self.assertNotEqual(copy.date, sheet.date)
        self.assertEqual(copy.state, 'draft')
        self.assertEqual(copy.line_ids.qty, 2)

    def test_user_records_sheets_but_cannot_manage_tags(self):
        Sheet = self.env['eh.daily.disbursement'].with_user(self.user)
        sheet = Sheet.create({'line_ids': [(0, 0, {'product_id': self.product_a.id, 'qty': 1})]})
        self.assertEqual(sheet.net_cost, 10)
        with self.assertRaises(AccessError):
            self.env['eh.daily.disbursement.tag'].with_user(self.user).create(
                {'name': 'X', 'code': 'x'})
        self.env['eh.daily.disbursement.tag'].with_user(self.manager).create(
            {'name': 'X', 'code': 'x'})

    def test_auditor_is_read_only(self):
        sheet = self._create_sheet([('out', self.product_a, 1)])
        self.assertEqual(sheet.with_user(self.auditor).net_cost, 10)
        with self.assertRaises(AccessError):
            sheet.with_user(self.auditor).write({'notes': 'tamper'})
        with self.assertRaises(AccessError):
            self.env['eh.daily.disbursement'].with_user(self.auditor).create({})

    def test_eh_manager_implies_disbursement_manager(self):
        eh_manager = self.env.ref('eh_account_base.group_eh_manager')
        self.assertIn(
            self.env.ref('eh_daily_disbursement.group_daily_disbursement_manager'),
            eh_manager.trans_implied_ids,
        )
