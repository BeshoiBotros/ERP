# -*- encoding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import api, fields, models
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError, ValidationError


class EhDiscountEntry(models.Model):
    _name = 'eh.discount.entry'
    _description = 'Discount Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: 'New')
    program_id = fields.Many2one('eh.discount.program', string='Discount Program', required=True, readonly=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, readonly=True)
    
    customer_id = fields.Many2one('res.partner', string='Customer', related='program_id.customer_id', store=True)
    company_id = fields.Many2one('res.company', string='Company', related='program_id.company_id', store=True)
    
    invoice_ids = fields.Many2many('account.move', string='Invoices', readonly=True, domain="[('partner_id', '=', customer_id), ('state', '=', 'posted'), ('move_type', '=', 'out_invoice')]")
    
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)
    total_invoiced = fields.Monetary(string='Total Invoiced', currency_field='currency_id', readonly=True)
    total_discount = fields.Monetary(string='Total Discount (Customer)', currency_field='currency_id', readonly=True)
    company_discount = fields.Monetary(string='Company Share (Expense)', currency_field='currency_id', readonly=True)
    vendor_total_discount = fields.Monetary(string='Vendors Share', currency_field='currency_id', readonly=True)
    
    vendor_line_ids = fields.One2many('eh.discount.vendor.line', 'entry_id', string='Vendor Distribution', readonly=True)
    
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('reversed', 'Reversed')
    ], string='Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('eh.discount.entry') or 'New'
        return super().create(vals_list)

    def action_post(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if not rec.program_id.discount_expense_account_id:
                raise UserError("Please configure a Discount Expense Account on the Discount Program.")
            if not rec.program_id.discount_journal_id:
                raise UserError("Please configure a Discount Journal on the Discount Program.")
            
            # Create Journal Entry
            move_vals = rec._prepare_journal_entry()
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            
            rec.write({
                'move_id': move.id,
                'state': 'posted'
            })

    def _prepare_journal_entry(self):
        self.ensure_one()
        
        # Determine customer accounts
        customer_account = self.customer_id.property_account_receivable_id
        if not customer_account:
            raise UserError("Please configure a receivable account for customer %s" % self.customer_id.name)
            
        line_vals = []
        
        # 1. Customer line (Credit) - Total Discount
        line_vals.append((0, 0, {
            'name': 'Discount: %s' % self.name,
            'partner_id': self.customer_id.id,
            'account_id': customer_account.id,
            'debit': 0.0,
            'credit': self.total_discount,
        }))
        
        # 2. Company expense line (Debit)
        line_vals.append((0, 0, {
            'name': 'Company Discount Share: %s' % self.name,
            'account_id': self.program_id.discount_expense_account_id.id,
            'debit': self.company_discount,
            'credit': 0.0,
        }))
        
        # 3. Vendor lines (Debit) - Vendor Share
        vendor_debit_indices = []  # track indices for rounding adjustment
        for vline in self.vendor_line_ids:
            if vline.discount_amount <= 0:
                continue
            vendor_account = vline.partner_id.property_account_payable_id
            if not vendor_account:
                raise UserError("Please configure a payable account for vendor %s" % vline.partner_id.name)
            line_vals.append((0, 0, {
                'name': 'Vendor Discount Share: %s' % self.name,
                'partner_id': vline.partner_id.id,
                'account_id': vendor_account.id,
                'debit': vline.discount_amount,
                'credit': 0.0,
            }))
            vendor_debit_indices.append(len(line_vals) - 1)
        
        # 4. Fallback: if no vendor lines but vendor share > 0, book it to expense account
        if not vendor_debit_indices and self.vendor_total_discount > 0:
            line_vals.append((0, 0, {
                'name': 'Unallocated Vendor Discount Share: %s' % self.name,
                'account_id': self.program_id.discount_expense_account_id.id,
                'debit': self.vendor_total_discount,
                'credit': 0.0,
            }))
            vendor_debit_indices.append(len(line_vals) - 1)
        
        # 5. Fix rounding: adjust last vendor debit line to ensure balance
        total_debit = sum(l[2]['debit'] for l in line_vals)
        total_credit = sum(l[2]['credit'] for l in line_vals)
        rounding_diff = round(total_credit - total_debit, 2)
        
        if abs(rounding_diff) > 0 and abs(rounding_diff) <= 0.10 and vendor_debit_indices:
            # Adjust last vendor debit line to absorb the rounding difference
            last_idx = vendor_debit_indices[-1]
            line_vals[last_idx][2]['debit'] = round(line_vals[last_idx][2]['debit'] + rounding_diff, 2)
        
        # 6. Final validation
        total_debit = sum(l[2]['debit'] for l in line_vals)
        total_credit = sum(l[2]['credit'] for l in line_vals)
        if abs(total_debit - total_credit) > 0.01:
            raise UserError(
                "Cannot create journal entry: debits (%.2f) != credits (%.2f). "
                "Please check vendor distribution." % (total_debit, total_credit)
            )
            
        return {
            'move_type': 'entry',
            'date': self.date,
            'journal_id': self.program_id.discount_journal_id.id,
            'ref': self.name,
            'line_ids': line_vals,
            'company_id': self.company_id.id,
        }

    def action_reverse(self):
        for rec in self:
            if rec.state != 'posted' or not rec.move_id:
                raise UserError("Only posted entries with a journal entry can be reversed.")
            
            # Reverse the journal entry
            default_values_list = [{
                'date': fields.Date.context_today(self),
                'ref': 'Reversal of %s' % rec.name,
            }]
            reversal = rec.move_id._reverse_moves(default_values_list, cancel=True)
            reversal.action_post()
            
            rec.write({
                'state': 'reversed'
            })
