# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Workflow, locking and integrity rules of daily sheets."""

from datetime import date

import psycopg2

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import EhDailyDisbursementCase


@tagged('post_install', '-at_install', 'eh_daily_disbursement')
class TestWorkflow(EhDailyDisbursementCase):

    def _confirmed_sheet(self, day=date(2026, 5, 1)):
        sheet = self._create_sheet([('out', self.product_a, 2)], date=day)
        sheet.with_user(self.user).action_confirm()
        return sheet

    # -- state machine -----------------------------------------------------

    def test_full_cycle_stamps_actors(self):
        sheet = self._confirmed_sheet()
        self.assertEqual(sheet.state, 'confirmed')
        self.assertEqual(sheet.confirmed_by_id, self.user)
        self.assertTrue(sheet.confirmed_date)
        sheet.with_user(self.manager).action_close()
        self.assertEqual(sheet.state, 'closed')
        self.assertEqual(sheet.closed_by_id, self.manager)
        self.assertEqual(sheet.line_ids.state, 'closed')
        sheet.with_user(self.manager).action_reset_to_draft()
        self.assertEqual(sheet.state, 'draft')
        self.assertFalse(sheet.confirmed_by_id or sheet.closed_by_id)

    def test_user_cannot_close_or_reset(self):
        sheet = self._confirmed_sheet()
        with self.assertRaises(UserError):
            sheet.with_user(self.user).action_close()
        with self.assertRaises(UserError):
            sheet.with_user(self.user).action_reset_to_draft()
        with self.assertRaises(UserError):
            sheet.with_user(self.user).action_cancel()
        sheet.with_user(self.manager).action_cancel()
        self.assertEqual(sheet.state, 'cancelled')

    def test_user_can_cancel_draft(self):
        sheet = self._create_sheet(date=date(2026, 5, 2))
        sheet.with_user(self.user).action_cancel()
        self.assertEqual(sheet.state, 'cancelled')

    def test_auditor_cannot_run_actions(self):
        sheet = self._create_sheet([('out', self.product_a, 1)], date=date(2026, 5, 3))
        with self.assertRaises(UserError):
            sheet.with_user(self.auditor).action_confirm()

    def test_confirm_requires_lines(self):
        sheet = self._create_sheet(date=date(2026, 5, 4))
        with self.assertRaises(UserError):
            sheet.with_user(self.user).action_confirm()

    def test_wrong_transitions_refused(self):
        sheet = self._create_sheet([('out', self.product_a, 1)], date=date(2026, 5, 5))
        with self.assertRaises(UserError):
            sheet.with_user(self.manager).action_close()          # from draft
        with self.assertRaises(UserError):
            sheet.with_user(self.manager).action_reset_to_draft()  # already draft
        sheet.with_user(self.user).action_confirm()
        sheet.with_user(self.manager).action_close()
        with self.assertRaises(UserError):
            sheet.with_user(self.manager).action_cancel()         # closed

    # -- workflow guard (no RPC bypass) -------------------------------------

    def test_direct_state_write_refused(self):
        sheet = self._create_sheet([('out', self.product_a, 1)], date=date(2026, 5, 6))
        for user in (self.user, self.manager):
            with self.assertRaises(AccessError):
                sheet.with_user(user).write({'state': 'closed'})
            with self.assertRaises(AccessError):
                sheet.with_user(user).write({'closed_by_id': user.id})

    def test_create_cannot_start_in_guarded_state(self):
        sheet = self.env['eh.daily.disbursement'].with_user(self.user).create({
            'date': date(2026, 5, 7), 'state': 'closed',
            'closed_by_id': self.user.id,
        })
        self.assertEqual(sheet.state, 'draft')
        self.assertFalse(sheet.closed_by_id)

    # -- locking -----------------------------------------------------------

    def test_lines_locked_outside_draft(self):
        sheet = self._confirmed_sheet()
        line = sheet.line_ids
        with self.assertRaises(UserError):
            line.qty = 5
        with self.assertRaises(UserError):
            self.env['eh.daily.disbursement.line'].create({
                'sheet_id': sheet.id, 'product_id': self.product_b.id, 'qty': 1})
        with self.assertRaises(UserError):
            line.unlink()
        with self.assertRaises(UserError):
            sheet.write({'line_ids': [(0, 0, {'product_id': self.product_b.id, 'qty': 1})]})

    def test_line_cannot_move_into_locked_sheet(self):
        locked = self._confirmed_sheet()
        draft = self._create_sheet([('out', self.product_b, 1)], date=date(2026, 5, 8))
        with self.assertRaises(UserError):
            draft.line_ids.sheet_id = locked

    def test_identity_frozen_but_notes_editable(self):
        sheet = self._confirmed_sheet()
        with self.assertRaises(UserError):
            sheet.date = date(2026, 6, 1)
        with self.assertRaises(UserError):
            sheet.tag_id = False
        sheet.notes = '<p>Late delivery</p>'
        sheet.responsible_id = self.manager
        self.assertEqual(sheet.responsible_id, self.manager)

    def test_reset_unlocks_lines(self):
        sheet = self._confirmed_sheet()
        sheet.with_user(self.manager).action_reset_to_draft()
        sheet.line_ids.qty = 4
        self.assertEqual(sheet.net_cost, 40)

    def test_only_draft_sheets_deleted(self):
        sheet = self._confirmed_sheet()
        with self.assertRaises(UserError):
            sheet.unlink()
        sheet.with_user(self.manager).action_cancel()
        with self.assertRaises(UserError):
            sheet.unlink()
        draft = self._create_sheet(date=date(2026, 5, 9))
        draft.unlink()
        self.assertFalse(draft.exists())

    # -- one sheet per company / day / tag ---------------------------------

    def test_duplicate_day_refused(self):
        self._create_sheet(date=date(2026, 5, 10))
        with self.assertRaises(ValidationError):
            self._create_sheet(date=date(2026, 5, 10))

    def test_duplicate_day_without_tag_refused(self):
        self._create_sheet(date=date(2026, 5, 11), tag_id=False)
        with self.assertRaises(ValidationError):
            self._create_sheet(date=date(2026, 5, 11), tag_id=False)

    def test_other_tag_or_cancelled_sheet_allowed(self):
        first = self._create_sheet(date=date(2026, 5, 12))
        self._create_sheet(date=date(2026, 5, 12), tag_id=False)
        first.action_cancel()
        replacement = self._create_sheet(date=date(2026, 5, 12))
        self.assertEqual(replacement.state, 'draft')
        # Reviving the cancelled sheet would now clash with its replacement.
        with self.assertRaises(ValidationError):
            first.action_reset_to_draft()

    def test_database_backstop_for_duplicate_day(self):
        sheet = self._create_sheet(date=date(2026, 5, 13))
        self.env.flush_all()
        cr = self.env.cr
        try:
            with mute_logger('odoo.sql_db'), self.assertRaises(psycopg2.errors.ExclusionViolation), cr.savepoint():
                cr.execute("""
                    INSERT INTO eh_daily_disbursement (name, date, company_id, tag_id, state)
                    SELECT name || '-dup', date, company_id, tag_id, 'draft'
                    FROM eh_daily_disbursement WHERE id = %s
                """, [sheet.id])
                cr.execute("SET CONSTRAINTS ALL IMMEDIATE")
        finally:
            cr.execute("SET CONSTRAINTS ALL DEFERRED")

    # -- line rules ----------------------------------------------------------

    def test_quantity_must_be_positive(self):
        for qty in (0, -1):
            with self.assertRaises(ValidationError):
                self._create_sheet([('out', self.product_a, qty)], date=date(2026, 5, 14))

    def test_unit_cost_not_negative(self):
        with self.assertRaises(ValidationError):
            self._create_sheet([('out', self.product_a, 1, -2.0)], date=date(2026, 5, 15))

    def test_product_must_match_tag_categories(self):
        outsider = self.env['product.product'].create({
            'name': 'Hammer', 'categ_id': self.categ_other.id})
        with self.assertRaises(ValidationError):
            self._create_sheet([('out', outsider, 1)], date=date(2026, 5, 16))
        # Child categories of an allowed category are accepted.
        child = self.env['product.category'].create({
            'name': 'Mini', 'parent_id': self.categ_perfume.id})
        mini = self.env['product.product'].create({'name': 'Mini A', 'categ_id': child.id})
        self._create_sheet([('out', mini, 1)], date=date(2026, 5, 17))

    def test_tag_change_rechecks_lines(self):
        outsider = self.env['product.product'].create({
            'name': 'Hammer', 'categ_id': self.categ_other.id})
        sheet = self._create_sheet([('out', outsider, 1)], date=date(2026, 5, 18), tag_id=False)
        with self.assertRaises(ValidationError):
            sheet.tag_id = self.tag

    # -- tags ----------------------------------------------------------------

    def test_shared_tag_code_unique(self):
        Tag = self.env['eh.daily.disbursement.tag']
        Tag.create({'name': 'Shared', 'code': 'shared'})
        with self.assertRaises(ValidationError):
            Tag.create({'name': 'Shared again', 'code': 'shared'})
        # The same code in a specific company is a different scope.
        Tag.create({'name': 'Company', 'code': 'shared', 'company_id': self.company.id})
