# -*- encoding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import api, fields, models
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError


class EhDiscountComputeVendorWizard(models.TransientModel):
    _name = 'eh.discount.compute.vendor.wizard'
    _description = 'Compute Discount Vendor Helper'

    wizard_id = fields.Many2one('eh.discount.compute.wizard', string='Wizard', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True)
    invoiced_amount = fields.Float(string='Invoiced Amount')
    percentage = fields.Float(string='%', digits=(16, 4))
    discount_amount = fields.Float(string='Discount Amount')


class EhDiscountComputeWizard(models.TransientModel):
    _name = 'eh.discount.compute.wizard'
    _description = 'Compute Discount Wizard'

    program_id = fields.Many2one('eh.discount.program', string='Discount Program', required=True)
    date_from = fields.Date(string='Start Date', related='program_id.date_from')
    date_to = fields.Date(string='End Date', related='program_id.date_to')
    customer_id = fields.Many2one('res.partner', string='Customer', related='program_id.customer_id')
    
    invoice_ids = fields.Many2many('account.move', string='Invoices')
    total_invoiced = fields.Float(string='Total Invoiced', readonly=True)
    total_discount = fields.Float(string='Total Discount', readonly=True)
    company_discount = fields.Float(string='Company Share', readonly=True)
    vendor_discount = fields.Float(string='Vendors Share', readonly=True)
    
    vendor_line_ids = fields.One2many('eh.discount.compute.vendor.wizard', 'wizard_id', string='Vendors')

    @api.onchange('program_id')
    def _onchange_program_id(self):
        if not self.program_id:
            return
            
        domain = [
            ('partner_id', '=', self.program_id.customer_id.id),
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', self.program_id.date_from),
            ('invoice_date', '<=', self.program_id.date_to),
        ]
        invoices = self.env['account.move'].search(domain)
        self.invoice_ids = [(6, 0, invoices.ids)]
        
        self._recalculate_all_totals()

    @api.onchange('invoice_ids')
    def _onchange_invoice_ids(self):
        self._recalculate_all_totals()

    def _recalculate_all_totals(self):
        if not self.program_id:
            return

        self.total_invoiced = sum(self.invoice_ids.mapped('amount_untaxed'))
        
        self.total_discount = self.total_invoiced * (self.program_id.total_discount_pct / 100.0)
        self.company_discount = self.total_invoiced * (self.program_id.company_share_pct / 100.0)
        self.vendor_discount = self.total_discount - self.company_discount

        # Compute vendor amounts from invoice lines
        vendor_totals = {}
        for inv in self.invoice_ids:
            for line in inv.invoice_line_ids:
                if line.product_id and line.price_subtotal > 0:
                    # Try to find vendor from product's sellers or PO lines (if any)
                    vendor = False
                    if hasattr(line, 'purchase_line_id') and line.purchase_line_id:
                        vendor = line.purchase_line_id.order_id.partner_id
                    elif line.product_id.seller_ids:
                        vendor = line.product_id.seller_ids[0].partner_id
                    
                    if vendor:
                        vendor_totals[vendor.id] = vendor_totals.get(vendor.id, 0.0) + line.price_subtotal
                        
        vendor_lines = []
        vendor_invoiced_total = sum(vendor_totals.values())
        
        for vendor_id, amount in vendor_totals.items():
            pct = (amount / vendor_invoiced_total) if vendor_invoiced_total > 0 else 0
            v_discount = self.vendor_discount * pct
            vendor_lines.append((0, 0, {
                'partner_id': vendor_id,
                'invoiced_amount': amount,
                'percentage': pct,
                'discount_amount': v_discount
            }))
            
        self.vendor_line_ids = [(5, 0, 0)] + vendor_lines

    def action_recalculate(self):
        # Recalculate based on manual overrides
        vendor_invoiced_total = sum(line.invoiced_amount for line in self.vendor_line_ids)
        for line in self.vendor_line_ids:
            if vendor_invoiced_total > 0:
                line.percentage = (line.invoiced_amount / vendor_invoiced_total)
                line.discount_amount = self.vendor_discount * line.percentage
            else:
                line.percentage = 0
                line.discount_amount = 0
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Compute Discount',
            'res_model': 'eh.discount.compute.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _compute_vendor_distribution(self, invoices):
        """Compute vendor totals from invoice lines (backend-safe)."""
        vendor_totals = {}
        for inv in invoices:
            for line in inv.invoice_line_ids:
                if line.product_id and line.price_subtotal > 0:
                    vendor = False
                    if hasattr(line, 'purchase_line_id') and line.purchase_line_id:
                        vendor = line.purchase_line_id.order_id.partner_id
                    elif line.product_id.seller_ids:
                        vendor = line.product_id.seller_ids[0].partner_id
                    if vendor:
                        vendor_totals[vendor.id] = vendor_totals.get(vendor.id, 0.0) + line.price_subtotal
        return vendor_totals

    def action_create_entry(self):
        if not self.invoice_ids:
            raise UserError("Please select at least one invoice.")

        # Recalculate totals from invoices (backend-safe, ignores readonly UI values)
        total_invoiced = sum(self.invoice_ids.mapped('amount_untaxed'))
        total_discount = total_invoiced * (self.program_id.total_discount_pct / 100.0)
        company_discount = total_invoiced * (self.program_id.company_share_pct / 100.0)
        vendor_discount = total_discount - company_discount

        # Build vendor vals — use wizard lines if available, otherwise recompute
        vendor_vals = []
        if self.vendor_line_ids:
            for vline in self.vendor_line_ids:
                vendor_vals.append((0, 0, {
                    'partner_id': vline.partner_id.id,
                    'invoiced_amount': vline.invoiced_amount,
                    'percentage_of_total': vline.percentage,
                    'discount_amount': vline.discount_amount,
                }))
        else:
            # Fallback: recompute vendor distribution in backend
            vendor_totals = self._compute_vendor_distribution(self.invoice_ids)
            vendor_invoiced_total = sum(vendor_totals.values())
            for vid, amount in vendor_totals.items():
                pct = (amount / vendor_invoiced_total) if vendor_invoiced_total > 0 else 0
                v_discount = vendor_discount * pct
                vendor_vals.append((0, 0, {
                    'partner_id': vid,
                    'invoiced_amount': amount,
                    'percentage_of_total': pct,
                    'discount_amount': v_discount,
                }))

        entry = self.env['eh.discount.entry'].create({
            'program_id': self.program_id.id,
            'invoice_ids': [(6, 0, self.invoice_ids.ids)],
            'total_invoiced': total_invoiced,
            'total_discount': total_discount,
            'company_discount': company_discount,
            'vendor_total_discount': vendor_discount,
            'vendor_line_ids': vendor_vals,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Discount Entry',
            'res_model': 'eh.discount.entry',
            'res_id': entry.id,
            'view_mode': 'form',
        }

