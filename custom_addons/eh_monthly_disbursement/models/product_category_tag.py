# -*- encoding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import fields, models


class EhProductCategoryTag(models.Model):
    _name = 'eh.product.category.tag'
    _description = 'Product Category Tag'
    _order = 'name'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Category tag code must be unique!')
    ]
