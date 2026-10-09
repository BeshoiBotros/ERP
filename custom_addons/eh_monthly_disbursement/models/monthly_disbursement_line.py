# -*- encoding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import api, fields, models


class EhMonthlyDisbursementLine(models.Model):
    _name = 'eh.monthly.disbursement.line'
    _description = 'Monthly Disbursement Line'

    disbursement_id = fields.Many2one('eh.monthly.disbursement', string='Disbursement', required=True, ondelete='cascade')
    
    move_type = fields.Selection([
        ('out', 'Disbursement'),
        ('return', 'Return')
    ], string='Move Type', required=True, default='out')
    
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_categ_id = fields.Many2one('product.category', string='Product Category', related='product_id.categ_id', store=True)
    
    category_tag_id = fields.Many2one('eh.product.category.tag', string='Category Tag', related='disbursement_id.category_tag_id', store=True)
    
    purchase_price = fields.Float(string='Purchase Price', required=True, default=0.0)
    qty = fields.Float(string='Quantity', required=True, default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', store=True)
    
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='disbursement_id.currency_id')
    
    notes = fields.Char(string='Notes')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # We fetch standard_price which is generally the cost price
            self.purchase_price = self.product_id.standard_price

    @api.depends('purchase_price', 'qty')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.purchase_price * line.qty
