# -*- encoding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import api, fields, models
import calendar
from datetime import date


class EhMonthlyDisbursement(models.Model):
    _name = 'eh.monthly.disbursement'
    _description = 'Monthly Disbursement'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: 'New')
    
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'),
        ('4', 'April'), ('5', 'May'), ('6', 'June'),
        ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Month', required=True, tracking=True, default=lambda self: str(fields.Date.today().month))
    
    year = fields.Integer(string='Year', required=True, tracking=True, default=lambda self: fields.Date.today().year)
    
    date_from = fields.Date(string='Start Date', compute='_compute_dates', store=True)
    date_to = fields.Date(string='End Date', compute='_compute_dates', store=True)
    
    category_tag_id = fields.Many2one('eh.product.category.tag', string='Category Tag', tracking=True)
    
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    notes = fields.Text(string='Notes')
    
    line_ids = fields.One2many('eh.monthly.disbursement.line', 'disbursement_id', string='All Lines')
    
    disbursement_line_ids = fields.One2many(
        'eh.monthly.disbursement.line', 'disbursement_id', 
        string='Disbursement Lines', 
        domain=[('move_type', '=', 'out')]
    )
    
    return_line_ids = fields.One2many(
        'eh.monthly.disbursement.line', 'disbursement_id', 
        string='Return Lines', 
        domain=[('move_type', '=', 'return')]
    )
    
    # Computed fields for Disbursement (Out)
    total_disbursed_qty = fields.Float(string='Total Disbursed Qty', compute='_compute_totals', store=True)
    total_disbursed_cost = fields.Monetary(string='Total Disbursed Cost', compute='_compute_totals', store=True, currency_field='currency_id')
    
    # Computed fields for Returns
    total_returned_qty = fields.Float(string='Total Returned Qty', compute='_compute_totals', store=True)
    total_returned_cost = fields.Monetary(string='Total Returned Cost', compute='_compute_totals', store=True, currency_field='currency_id')
    
    # Net computed fields
    net_qty = fields.Float(string='Net Quantity', compute='_compute_totals', store=True)
    net_cost = fields.Monetary(string='Net Cost', compute='_compute_totals', store=True, currency_field='currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('eh.monthly.disbursement') or 'New'
        return super().create(vals_list)

    @api.depends('month', 'year')
    def _compute_dates(self):
        for rec in self:
            if rec.month and rec.year:
                try:
                    month_int = int(rec.month)
                    rec.date_from = date(rec.year, month_int, 1)
                    last_day = calendar.monthrange(rec.year, month_int)[1]
                    rec.date_to = date(rec.year, month_int, last_day)
                except ValueError:
                    rec.date_from = False
                    rec.date_to = False
            else:
                rec.date_from = False
                rec.date_to = False

    @api.depends('disbursement_line_ids.qty', 'disbursement_line_ids.subtotal', 'return_line_ids.qty', 'return_line_ids.subtotal')
    def _compute_totals(self):
        for rec in self:
            rec.total_disbursed_qty = sum(rec.disbursement_line_ids.mapped('qty'))
            rec.total_disbursed_cost = sum(rec.disbursement_line_ids.mapped('subtotal'))
            
            rec.total_returned_qty = sum(rec.return_line_ids.mapped('qty'))
            rec.total_returned_cost = sum(rec.return_line_ids.mapped('subtotal'))
            
            rec.net_qty = rec.total_disbursed_qty - rec.total_returned_qty
            rec.net_cost = rec.total_disbursed_cost - rec.total_returned_cost

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})
