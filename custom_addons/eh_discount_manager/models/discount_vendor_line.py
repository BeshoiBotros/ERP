# -*- encoding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import api, fields, models


class EhDiscountVendorLine(models.Model):
    _name = 'eh.discount.vendor.line'
    _description = 'Discount Vendor Line'

    entry_id = fields.Many2one('eh.discount.entry', string='Discount Entry', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True)
    currency_id = fields.Many2one('res.currency', related='entry_id.currency_id')
    
    invoiced_amount = fields.Monetary(string='Invoiced Amount', currency_field='currency_id', required=True)
    percentage_of_total = fields.Float(string='% of Total', digits=(16, 4))
    discount_amount = fields.Monetary(string='Discount Amount', currency_field='currency_id', required=True)

