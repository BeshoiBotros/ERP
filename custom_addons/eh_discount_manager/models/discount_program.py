# -*- encoding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import api, fields, models
# pyrefly: ignore [missing-import]
from odoo.exceptions import ValidationError


class EhDiscountProgram(models.Model):
    _name = 'eh.discount.program'
    _description = 'Discount Program'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    discount_type_id = fields.Many2one('eh.discount.type', string='Discount Type', required=True, tracking=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True, help="Customer eligible for this discount.")
    
    total_discount_pct = fields.Float(string='Total Discount (%)', required=True, tracking=True, help="E.g., 5.0 for 5%")
    company_share_pct = fields.Float(string='Company Share (%)', required=True, tracking=True, help="E.g., 3.5 for 3.5%")
    vendor_share_pct = fields.Float(string='Vendor Share (%)', compute='_compute_vendor_share_pct', store=True, tracking=True)
    
    discount_expense_account_id = fields.Many2one('account.account', string='Discount Expense Account', domain="[('account_type', 'in', ('expense', 'expense_direct_cost'))]")
    discount_journal_id = fields.Many2one('account.journal', string='Discount Journal', domain="[('type', '=', 'general')]")
    
    date_from = fields.Date(string='Start Date', required=True, tracking=True)
    date_to = fields.Date(string='End Date', required=True, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    entry_ids = fields.One2many('eh.discount.entry', 'program_id', string='Discount Entries')
    notes = fields.Text(string='Notes')

    @api.depends('total_discount_pct', 'company_share_pct')
    def _compute_vendor_share_pct(self):
        for rec in self:
            rec.vendor_share_pct = rec.total_discount_pct - rec.company_share_pct

    @api.constrains('total_discount_pct', 'company_share_pct')
    def _check_percentages(self):
        for rec in self:
            if rec.total_discount_pct <= 0:
                raise ValidationError("Total Discount (%) must be greater than zero.")
            if rec.company_share_pct < 0:
                raise ValidationError("Company Share (%) cannot be negative.")
            if rec.company_share_pct > rec.total_discount_pct:
                raise ValidationError("Company Share (%) cannot exceed Total Discount (%).")

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})
