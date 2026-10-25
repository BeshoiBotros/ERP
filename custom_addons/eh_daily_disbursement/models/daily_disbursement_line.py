# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""
eh.daily.disbursement.line: one product movement on a daily sheet.

unit_cost snapshots the product cost when the line is created (or its
product changes), so later cost updates never rewrite past days. Because
it is a stored compute rather than an onchange, lines created by import
or RPC get the cost too; an explicitly supplied unit_cost is kept.

signed_qty / signed_subtotal are positive for disbursements and negative
for returns, so a net figure over any period is a plain SUM.

Lines are editable only while their sheet is draft, for everyone: the
figures of a confirmed or closed day change through a reset to draft.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class EhDailyDisbursementLine(models.Model):
    _name = 'eh.daily.disbursement.line'
    _description = "Daily Disbursement Line"
    _order = 'sheet_id, sequence, id'
    _check_company_auto = True

    sheet_id = fields.Many2one(
        'eh.daily.disbursement', string="Sheet", required=True,
        index=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    move_type = fields.Selection([
        ('out', 'Disbursement'),
        ('return', 'Return'),
    ], string="Type", required=True, default='out')

    product_id = fields.Many2one(
        'product.product', required=True, index=True, check_company=True,
        domain=[('type', '!=', 'service')],
    )
    product_categ_id = fields.Many2one(
        'product.category', string="Product Category",
        related='product_id.categ_id', store=True,
    )
    uom_id = fields.Many2one(
        'uom.uom', string="Unit of Measure",
        related='product_id.uom_id', store=True,
    )
    qty = fields.Float(
        string="Quantity", required=True, default=1.0,
        digits='Product Unit of Measure',
    )
    unit_cost = fields.Float(
        compute='_compute_unit_cost', store=True, readonly=False,
        precompute=True, digits='Product Price',
    )
    subtotal = fields.Monetary(compute='_compute_subtotal', store=True)
    signed_qty = fields.Float(
        compute='_compute_signed', store=True,
        digits='Product Unit of Measure',
    )
    signed_subtotal = fields.Monetary(compute='_compute_signed', store=True)
    note = fields.Char()

    # Sheet fields copied onto the line so line-level analysis (pivot,
    # graph, dashboard) can filter and group without a join.
    date = fields.Date(related='sheet_id.date', store=True, index=True)
    company_id = fields.Many2one(
        related='sheet_id.company_id', store=True, index=True,
    )
    currency_id = fields.Many2one(related='sheet_id.currency_id', store=True)
    tag_id = fields.Many2one(related='sheet_id.tag_id', store=True, index=True)
    state = fields.Selection(related='sheet_id.state', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.sheet_id._check_lines_editable()
        return lines

    def write(self, vals):
        self.sheet_id._check_lines_editable()
        if vals.get('sheet_id'):
            self.env['eh.daily.disbursement'].browse(vals['sheet_id'])._check_lines_editable()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_only_draft_sheet(self):
        self.sheet_id._check_lines_editable()

    @api.depends('product_id')
    def _compute_unit_cost(self):
        for line in self:
            company = line.sheet_id.company_id or self.env.company
            line.unit_cost = line.product_id.with_company(company).standard_price

    @api.depends('qty', 'unit_cost')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty * line.unit_cost

    @api.depends('move_type', 'qty', 'subtotal')
    def _compute_signed(self):
        for line in self:
            sign = -1 if line.move_type == 'return' else 1
            line.signed_qty = sign * line.qty
            line.signed_subtotal = sign * line.subtotal

    @api.constrains('qty', 'unit_cost')
    def _check_amounts(self):
        for line in self:
            rounding = line.uom_id.rounding or 0.01
            if float_compare(line.qty, 0.0, precision_rounding=rounding) <= 0:
                raise ValidationError(_(
                    "%(product)s: quantity must be greater than zero. Record "
                    "a return as a Return line, not a negative quantity.",
                    product=line.product_id.display_name,
                ))
            if line.unit_cost < 0:
                raise ValidationError(_(
                    "%(product)s: unit cost cannot be negative.",
                    product=line.product_id.display_name,
                ))

    @api.constrains('product_id', 'sheet_id')
    def _check_product_in_tag_categories(self):
        for line in self:
            allowed = line.sheet_id.tag_id.product_categ_ids
            if allowed and not self.env['product.category'].search_count([
                    ('id', '=', line.product_categ_id.id),
                    ('id', 'child_of', allowed.ids)]):
                raise ValidationError(_(
                    "%(product)s (%(categ)s) is outside the categories of "
                    "tag %(tag)s.",
                    product=line.product_id.display_name,
                    categ=line.product_categ_id.display_name,
                    tag=line.sheet_id.tag_id.display_name,
                ))
