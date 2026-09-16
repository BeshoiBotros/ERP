# -*- encoding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import fields, models


class EhDiscountType(models.Model):
    _name = 'eh.discount.type'
    _description = 'Discount Type'
    _order = 'name'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Selection([
        ('annual', 'Annual Discount'),
        ('per_invoice', 'Per-Invoice Discount'),
        ('quarterly', 'Quarterly Discount'),
        ('semi_annual', 'Semi-Annual Discount'),
    ], string='Code', required=True, unique=True)
    active = fields.Boolean(default=True)
