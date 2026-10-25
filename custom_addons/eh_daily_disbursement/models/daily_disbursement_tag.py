# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""
Category tags for daily disbursement sheets (e.g. Perfumes, Nail Polish).

A tag groups sheets for filtering and dashboard breakdowns. When it lists
product categories, lines on a sheet carrying the tag may only pick
products from those categories (or their children).
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EhDailyDisbursementTag(models.Model):
    _name = 'eh.daily.disbursement.tag'
    _description = "Daily Disbursement Tag"
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        help="Short technical identifier, unique per company.",
    )
    sequence = fields.Integer(default=10)
    color = fields.Integer(
        help="Colour used for this tag in lists and dashboard charts.",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', index=True,
        help="Leave empty to share the tag across all companies.",
    )
    product_categ_ids = fields.Many2many(
        'product.category', string="Product Categories",
        help=(
            "When set, sheets with this tag only accept products from "
            "these categories or their children."
        ),
    )

    # unique(code, company_id) would let shared tags (company NULL) repeat a
    # code, since NULLs never collide; fold NULL to 0. DEFERRED so the
    # Python constraint below reports first with a readable message.
    _sql_constraints = [
        ('unique_code',
         "EXCLUDE USING btree (code WITH =, (COALESCE(company_id, 0)) WITH =) "
         "DEFERRABLE INITIALLY DEFERRED",
         "A tag code must be unique per company."),
    ]

    @api.constrains('code', 'company_id')
    def _check_code_unique(self):
        for tag in self:
            if self.with_context(active_test=False).search_count([
                    ('id', '!=', tag.id),
                    ('code', '=', tag.code),
                    ('company_id', '=', tag.company_id.id)]):
                if tag.company_id:
                    raise ValidationError(_(
                        "Tag code %(code)s is already used in %(company)s.",
                        code=tag.code, company=tag.company_id.name,
                    ))
                raise ValidationError(_(
                    "Tag code %(code)s is already used by a shared tag.",
                    code=tag.code,
                ))
