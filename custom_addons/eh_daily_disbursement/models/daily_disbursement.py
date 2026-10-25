# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""
eh.daily.disbursement: one sheet per company, day and (optional) tag.

The sheet owns the date; its lines inherit it through a stored related
field, so a line can never disagree with its sheet about which day it
belongs to. Totals are stored so list views and the dashboard can sum
them without touching the lines.

Workflow:  draft -> confirmed (User) -> closed (Manager)
           draft / confirmed -> cancelled, any non-draft -> draft (Manager)

The state machine is enforced by eh.workflow.guard: 'state' and the
confirm / close stamps change only through the actions below, never a
direct write. Outside draft the sheet's identity (date, tag, company) and
its lines are frozen for everyone; correct a sheet by resetting it.

A daily cron puts a "confirm sheet" activity on drafts whose day has
passed; confirming the sheet marks it done, cancelling removes it.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


GROUP_USER = 'eh_daily_disbursement.group_daily_disbursement_user'
GROUP_MANAGER = 'eh_daily_disbursement.group_daily_disbursement_manager'
ACTIVITY_CONFIRM = 'eh_daily_disbursement.mail_activity_confirm_sheet'

# Sheet fields that define which day / scope the figures belong to.
_FROZEN_AFTER_DRAFT = (
    'date', 'tag_id', 'company_id',
    'line_ids', 'disbursement_line_ids', 'return_line_ids',
)


class EhDailyDisbursement(models.Model):
    _name = 'eh.daily.disbursement'
    _description = "Daily Disbursement"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'eh.workflow.guard',
                'eh.cron.batch.mixin']
    _order = 'date desc, id desc'
    _check_company_auto = True

    _eh_guarded_fields = (
        'state', 'confirmed_by_id', 'confirmed_date',
        'closed_by_id', 'closed_date',
    )

    name = fields.Char(
        string="Reference", required=True, readonly=True, copy=False,
        default=lambda self: _('New'),
    )
    date = fields.Date(
        required=True, index=True, tracking=True, copy=False,
        default=fields.Date.context_today,
    )
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', store=True,
    )
    tag_id = fields.Many2one(
        'eh.daily.disbursement.tag', string="Category Tag",
        index=True, tracking=True, check_company=True,
    )
    responsible_id = fields.Many2one(
        'res.users', string="Responsible", tracking=True,
        default=lambda self: self.env.user,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, readonly=True, copy=False,
        index=True, tracking=True)
    notes = fields.Html()

    confirmed_by_id = fields.Many2one(
        'res.users', string="Confirmed By", readonly=True, copy=False,
    )
    confirmed_date = fields.Datetime(
        string="Confirmed On", readonly=True, copy=False,
    )
    closed_by_id = fields.Many2one(
        'res.users', string="Closed By", readonly=True, copy=False,
    )
    closed_date = fields.Datetime(
        string="Closed On", readonly=True, copy=False,
    )

    line_ids = fields.One2many(
        'eh.daily.disbursement.line', 'sheet_id', string="Lines", copy=True,
    )
    # Per-direction views of line_ids for the form's two tabs.
    disbursement_line_ids = fields.One2many(
        'eh.daily.disbursement.line', 'sheet_id',
        string="Disbursed Lines", domain=[('move_type', '=', 'out')],
    )
    return_line_ids = fields.One2many(
        'eh.daily.disbursement.line', 'sheet_id',
        string="Returned Lines", domain=[('move_type', '=', 'return')],
    )
    allowed_categ_ids = fields.Many2many(
        'product.category', compute='_compute_allowed_categ_ids',
        help="Categories lines may pick products from (tag restriction).",
    )

    disbursed_qty = fields.Float(
        string="Disbursed Qty", compute='_compute_totals', store=True,
        digits='Product Unit of Measure',
    )
    disbursed_cost = fields.Monetary(
        string="Disbursed Cost", compute='_compute_totals', store=True,
        tracking=True,
    )
    returned_qty = fields.Float(
        string="Returned Qty", compute='_compute_totals', store=True,
        digits='Product Unit of Measure',
    )
    returned_cost = fields.Monetary(
        string="Returned Cost", compute='_compute_totals', store=True,
        tracking=True,
    )
    net_qty = fields.Float(
        string="Net Qty", compute='_compute_totals', store=True,
        digits='Product Unit of Measure',
    )
    net_cost = fields.Monetary(
        string="Net Cost", compute='_compute_totals', store=True,
    )
    line_count = fields.Integer(compute='_compute_totals', store=True)

    # Backstop for _check_unique_day under concurrency: two users saving the
    # same day at once both pass the Python check; only one commit survives.
    # NULL tag folds to 0 so "no tag" is unique too. DEFERRED so that within
    # a transaction the Python constraint reports first, with a readable
    # message, instead of a raw unique-violation on INSERT.
    _sql_constraints = [
        ('unique_day',
         "EXCLUDE USING btree (company_id WITH =, date WITH =, "
         "(COALESCE(tag_id, 0)) WITH =) WHERE (state <> 'cancelled') "
         "DEFERRABLE INITIALLY DEFERRED",
         "A sheet already covers this day and tag in this company."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self._next_reference(
                    vals.get('date') or fields.Date.context_today(self))
        return super().create(vals_list)

    def write(self, vals):
        frozen = [f for f in _FROZEN_AFTER_DRAFT if f in vals]
        if frozen and self.filtered(lambda s: s.state != 'draft'):
            raise UserError(_(
                "Only draft sheets can change their date, tag, company or "
                "lines (%(fields)s). Reset the sheet to draft first.",
                fields=', '.join(frozen),
            ))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_only_draft(self):
        if self.filtered(lambda s: s.state != 'draft'):
            raise UserError(_(
                "Only draft sheets can be deleted. Cancel the sheet instead "
                "so its history is kept.",
            ))

    def _next_reference(self, date):
        # The prefix interpolates the SHEET date, not today: a sheet entered
        # late for yesterday must still read DD/<yesterday>/...
        date = fields.Date.to_date(date)
        return self.env['ir.sequence'].with_context(
            ir_sequence_date=date,
        ).next_by_code('eh.daily.disbursement', sequence_date=date) or _('New')

    @api.depends('tag_id.product_categ_ids')
    def _compute_allowed_categ_ids(self):
        # No restriction is expressed as "every root category", so the line
        # view can always apply ('categ_id', 'child_of', allowed_categ_ids).
        roots = self.env['product.category'].search([('parent_id', '=', False)])
        for sheet in self:
            sheet.allowed_categ_ids = sheet.tag_id.product_categ_ids or roots

    @api.depends('line_ids.move_type', 'line_ids.qty', 'line_ids.subtotal',
                 'line_ids.signed_qty', 'line_ids.signed_subtotal')
    def _compute_totals(self):
        for sheet in self:
            out = sheet.line_ids.filtered(lambda l: l.move_type == 'out')
            ret = sheet.line_ids - out
            sheet.disbursed_qty = sum(out.mapped('qty'))
            sheet.disbursed_cost = sum(out.mapped('subtotal'))
            sheet.returned_qty = sum(ret.mapped('qty'))
            sheet.returned_cost = sum(ret.mapped('subtotal'))
            sheet.net_qty = sum(sheet.line_ids.mapped('signed_qty'))
            sheet.net_cost = sum(sheet.line_ids.mapped('signed_subtotal'))
            sheet.line_count = len(sheet.line_ids)

    @api.constrains('company_id', 'date', 'tag_id', 'state')
    def _check_unique_day(self):
        for sheet in self.filtered(lambda s: s.state != 'cancelled'):
            clash = self.search([
                ('id', '!=', sheet.id),
                ('company_id', '=', sheet.company_id.id),
                ('date', '=', sheet.date),
                ('tag_id', '=', sheet.tag_id.id),
                ('state', '!=', 'cancelled'),
            ], limit=1)
            if clash:
                raise ValidationError(_(
                    "%(sheet)s already covers %(date)s for %(tag)s. Add the "
                    "lines there, or cancel it first.",
                    sheet=clash.display_name,
                    date=sheet.date,
                    tag=sheet.tag_id.display_name or _('no tag'),
                ))

    @api.constrains('tag_id')
    def _check_lines_match_tag(self):
        self.line_ids._check_product_in_tag_categories()

    def _check_lines_editable(self):
        locked = self.filtered(lambda s: s.state != 'draft')
        if locked:
            raise UserError(_(
                "The lines of %(sheets)s are locked because the sheet is no "
                "longer draft. Reset it to draft to change them.",
                sheets=', '.join(locked.mapped('display_name')),
            ))

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    def _check_group(self, xmlid, action):
        if not self.env.su and not self.env.user.has_group(xmlid):
            raise UserError(_(
                "You are not allowed to %(action)s daily disbursement "
                "sheets.",
                action=action,
            ))

    def _check_state(self, allowed, action):
        wrong = self.filtered(lambda s: s.state not in allowed)
        if wrong:
            raise UserError(_(
                "Cannot %(action)s %(sheets)s in its current status.",
                action=action,
                sheets=', '.join(wrong.mapped('display_name')),
            ))

    def action_confirm(self):
        self._check_group(GROUP_USER, _('confirm'))
        self._check_state(('draft',), _('confirm'))
        empty = self.filtered(lambda s: not s.line_ids)
        if empty:
            raise UserError(_(
                "%(sheets)s has no lines. Add what was disbursed or "
                "returned before confirming.",
                sheets=', '.join(empty.mapped('display_name')),
            ))
        self._eh_workflow_write({
            'state': 'confirmed',
            'confirmed_by_id': self.env.user.id,
            'confirmed_date': fields.Datetime.now(),
        })
        self.sudo().activity_feedback([ACTIVITY_CONFIRM])

    def action_close(self):
        self._check_group(GROUP_MANAGER, _('close'))
        self._check_state(('confirmed',), _('close'))
        self._eh_workflow_write({
            'state': 'closed',
            'closed_by_id': self.env.user.id,
            'closed_date': fields.Datetime.now(),
        })

    def action_cancel(self):
        # A user may drop their own draft; withdrawing a confirmed sheet is a
        # manager decision.
        self._check_state(('draft', 'confirmed'), _('cancel'))
        if self.filtered(lambda s: s.state == 'confirmed'):
            self._check_group(GROUP_MANAGER, _('cancel confirmed'))
        else:
            self._check_group(GROUP_USER, _('cancel'))
        self._eh_workflow_write({'state': 'cancelled'})
        self.sudo().activity_unlink([ACTIVITY_CONFIRM])

    def action_reset_to_draft(self):
        self._check_group(GROUP_MANAGER, _('reset'))
        self._check_state(('confirmed', 'closed', 'cancelled'), _('reset'))
        self._eh_workflow_write({
            'state': 'draft',
            'confirmed_by_id': False,
            'confirmed_date': False,
            'closed_by_id': False,
            'closed_date': False,
        })

    # ------------------------------------------------------------------
    # Entry helpers
    # ------------------------------------------------------------------

    def _previous_sheet(self):
        """Latest earlier non-cancelled sheet of the same company and tag
        that has lines; the template for a "same as last time" day."""
        self.ensure_one()
        return self.search([
            ('company_id', '=', self.company_id.id),
            ('tag_id', '=', self.tag_id.id),
            ('date', '<', self.date),
            ('state', '!=', 'cancelled'),
            ('line_count', '>', 0),
        ], order='date desc, id desc', limit=1)

    def action_copy_previous(self):
        """Fill an empty draft with the lines of the previous sheet.

        Quantities and types are copied; unit costs are NOT: each new line
        snapshots today's product cost, like a line typed in by hand.
        """
        self.ensure_one()
        self._check_group(GROUP_USER, _('fill'))
        self._check_state(('draft',), _('fill'))
        if self.line_ids:
            raise UserError(_(
                "%(sheet)s already has lines. Copying the previous sheet only "
                "fills an empty sheet.",
                sheet=self.display_name,
            ))
        previous = self._previous_sheet()
        if not previous:
            raise UserError(_(
                "No earlier sheet with lines exists for %(tag)s in "
                "%(company)s.",
                tag=self.tag_id.display_name or _('no tag'),
                company=self.company_id.name,
            ))
        self.write({'line_ids': [(0, 0, {
            'sequence': line.sequence,
            'move_type': line.move_type,
            'product_id': line.product_id.id,
            'qty': line.qty,
            'note': line.note,
        }) for line in previous.line_ids]})
        self.message_post(body=_(
            "Lines copied from %(sheet)s.", sheet=previous._get_html_link()))

    def action_view_lines(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'eh_daily_disbursement.action_daily_disbursement_line_analysis')
        action.update({
            'name': _('Lines of %s', self.display_name),
            'domain': [('sheet_id', '=', self.id)],
            'context': {'create': False},
        })
        return action

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------

    @api.model
    def _cron_remind_overdue_drafts(self):
        """Ask the responsible user to confirm drafts whose day has passed.

        One open reminder per sheet: a sheet that already carries one is
        skipped, so the cron can run daily without piling activities up.
        Each sheet runs in its own savepoint so one bad record (e.g. an
        archived responsible) never stops the rest of the batch.
        """
        activity_type = self.env.ref(ACTIVITY_CONFIRM)
        overdue = self.search([
            ('state', '=', 'draft'),
            ('date', '<', fields.Date.context_today(self)),
        ])
        pending = overdue.filtered(
            lambda s: activity_type not in s.activity_ids.activity_type_id)

        def remind(sheet):
            user = sheet.responsible_id or sheet.create_uid
            sheet.activity_schedule(
                ACTIVITY_CONFIRM,
                date_deadline=fields.Date.context_today(self),
                user_id=user.id,
                summary=_("Confirm the %(date)s sheet", date=sheet.date),
            )

        failures = self._eh_for_each_savepoint(
            pending, remind, log_label='daily disbursement reminder')
        return len(pending) - len(failures)
