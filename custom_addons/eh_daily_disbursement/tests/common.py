# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_daily_disbursement tests."""

from odoo.tests import new_test_user

from odoo.addons.eh_account_base.tests.common import EhAccountUnitTestCase


class EhDailyDisbursementCase(EhAccountUnitTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.categ_perfume = cls.env['product.category'].create({'name': 'Perfumes'})
        cls.categ_other = cls.env['product.category'].create({'name': 'Other'})
        cls.product_a = cls.env['product.product'].create({
            'name': 'Perfume A', 'categ_id': cls.categ_perfume.id,
            'standard_price': 10.0,
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'Perfume B', 'categ_id': cls.categ_perfume.id,
            'standard_price': 5.0,
        })
        cls.tag = cls.env['eh.daily.disbursement.tag'].create({
            'name': 'Perfumes', 'code': 'perfume',
            'product_categ_ids': [(6, 0, cls.categ_perfume.ids)],
        })
        cls.user = new_test_user(
            cls.env, login='dd_user',
            groups='eh_daily_disbursement.group_daily_disbursement_user',
        )
        cls.manager = new_test_user(
            cls.env, login='dd_manager',
            groups='eh_daily_disbursement.group_daily_disbursement_manager',
        )
        cls.auditor = new_test_user(
            cls.env, login='dd_auditor',
            groups='eh_account_base.group_eh_auditor',
        )

    @classmethod
    def _create_sheet(cls, lines=(), **vals):
        """Create a sheet; lines are (move_type, product, qty[, unit_cost])."""
        line_vals = []
        for line in lines:
            move_type, product, qty = line[:3]
            values = {'move_type': move_type, 'product_id': product.id, 'qty': qty}
            if len(line) > 3:
                values['unit_cost'] = line[3]
            line_vals.append((0, 0, values))
        return cls.env['eh.daily.disbursement'].create({
            'tag_id': cls.tag.id, 'line_ids': line_vals, **vals,
        })
