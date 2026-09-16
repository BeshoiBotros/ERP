# -*- encoding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import fields, models


class EhDiscountPurgeWizard(models.TransientModel):
    _name = 'eh.discount.purge.wizard'
    _description = 'Purge Discount Data Wizard'

    purge_mode = fields.Selection([
        ('all', 'Purge All Discount Data'),
        ('program', 'Purge Specific Program'),
    ], string='Purge Mode', default='all', required=True)
    
    program_id = fields.Many2one('eh.discount.program', string='Program to Purge')
    delete_programs = fields.Boolean(string='Delete Programs as well?', default=True, help="If checked, the Discount Programs will also be deleted.")

    def action_purge(self):
        if self.purge_mode == 'all':
            entries = self.env['eh.discount.entry'].search([])
        else:
            if not self.program_id:
                return
            entries = self.env['eh.discount.entry'].search([('program_id', '=', self.program_id.id)])
            
        # Reverse and cancel entries
        for entry in entries:
            if entry.state == 'posted' and entry.move_id:
                # Need to use standard Odoo reversal if possible, or just cancel the move if it's not strictly locked
                try:
                    reversal = entry.move_id._reverse_moves([{'date': fields.Date.context_today(self), 'ref': 'Purge'}], cancel=True)
                    reversal.action_post()
                except Exception:
                    # If reversal fails, try to just cancel it for testing purposes
                    entry.move_id.button_draft()
                    entry.move_id.button_cancel()
                    
            entry.write({'state': 'draft'})
            entry.move_id = False
            
        # Delete entries
        entries.unlink()
        
        if self.delete_programs:
            if self.purge_mode == 'all':
                self.env['eh.discount.program'].search([]).unlink()
            elif self.program_id:
                self.program_id.unlink()
                
        return {'type': 'ir.actions.client', 'tag': 'reload'}
