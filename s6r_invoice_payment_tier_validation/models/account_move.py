# Copyright 2026 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'tier.validation']

    _tier_validation_buttons_xpath = '/form/header/button[last()]'
    _state_field = 'invoice_payment_review_state'
    _state_from = ['to_review', 'in_review', 'declined']
    _state_to = ['approved']

    _tier_validation_manual_config = False
    SELECTION = [
        ('not_required', 'Not required'),
        ('to_review', 'To review'),
        ('in_review', 'In review'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]

    invoice_payment_review_state = fields.Selection(
        selection=SELECTION,
        string='Invoice Payment Review State',
        compute='_compute_invoice_payment_review_state',
        inverse='_inverse_invoice_payment_review_state',
        store=True,
        tracking=True,
        readonly=True,
        copy=False,
    )
    invoice_payment_review_state_auto = fields.Selection(
        selection=SELECTION,
        string='Invoice Payment Review State (Auto)',
        compute='_compute_invoice_payment_review_state',
        store=True,
        readonly=True,
        copy=False,
    )

    invoice_payment_review_state_manual = fields.Selection(
        selection=SELECTION,
        string='Invoice Payment Review State (Manual)',
        copy=False,
    )

    payment_locked = fields.Boolean(
        string='Payment Locked',
        compute='_compute_payment_locked',
        store=True,
        readonly=True,
    )

    @api.depends(
        'state',
        'validation_status',
        'payment_state',
        'is_intragroup_invoice',
        'invoice_payment_review_state_manual',
    )
    def _compute_invoice_payment_review_state(self):
        """
        Compute the Payment Review State for vendor bills/refunds.

        - Applies only to vendor bills and refunds.
        - AUTO state follows tier validation status.
        - Keeps previous value in draft or after payment to preserve history.
        - If validation is not required:
            intragroup => not_required, otherwise => False.
        - Manual override always takes priority.
        """
        status_map = {
            'validated': 'approved',
            'rejected': 'declined',
            'pending': 'in_review',
            'waiting': 'in_review',
        }
        for move in self:
            if move.move_type not in ('in_invoice', 'in_refund'):
                move.invoice_payment_review_state = False
                move.invoice_payment_review_state_auto = False
                continue
            mapped = status_map.get(move.validation_status)
            if mapped:
                auto_val = mapped
            elif move.state == 'draft' and move.invoice_payment_review_state:
                auto_val = move.invoice_payment_review_state
            elif not move._payment_validation_required():
                if move.is_intragroup_invoice:
                    auto_val = 'not_required'
                else:
                    auto_val = False
            else:
                auto_val = 'to_review'
            move.invoice_payment_review_state_auto = auto_val
            if move.invoice_payment_review_state_manual:
                move.invoice_payment_review_state = move.invoice_payment_review_state_manual
            else:
                move.invoice_payment_review_state = auto_val

    def _inverse_invoice_payment_review_state(self):
        """Allow only a specific group to manually override the computed state."""
        if self.env.context.get('skip_payment_review_manual_check'):
            return
        if not self.env.user.has_group(
            's6r_invoice_payment_tier_validation.group_payment_review_state_manual_override'):
            raise AccessError(
                _('You are not allowed to manually change the payment review state.'))
        for move in self:
            move.invoice_payment_review_state_manual = move.invoice_payment_review_state

    @api.depends('invoice_payment_review_state', 'state', 'partner_id')
    def _compute_payment_locked(self):
        """
        Lock payment if the bill is declined, or if validation is required
        and the review state is not 'approved' or 'not_required'.
        """
        allowed = {'approved', 'not_required'}
        for move in self:
            state = move.invoice_payment_review_state
            required = move._payment_validation_required()
            move.payment_locked = (state == 'declined') or (
                required and state not in allowed)

    def action_force_register_payment(self):
        """
           Prevent payment registration when the vendor bill is not approved for payment.

           If `payment_locked` is True, block the action with a clear error message.
           Otherwise, allow payment registration and bypass tier checks via context.
       """
        if any(m.payment_locked for m in self):
            raise UserError(
                _('Payment is not allowed: this vendor bill is not approved for payment.'))
        return super(AccountMove, self.with_context(
            skip_validation_check=True)).action_force_register_payment()

    def request_validation(self):
        """
        Request tier validation and reset any manual payment review override.

        When validation is (re)requested, the payment review state should follow the
        tier workflow again, so we clear `invoice_payment_review_state_manual`.
        """

        res = super(AccountMove, self).request_validation()
        for move in self:
            if move.invoice_payment_review_state_manual:
                move.invoice_payment_review_state_manual = False

        return res

    def restart_validation(self):
        """
        Request tier validation and reset any manual payment review override.

        When validation is restarted, the payment review state should follow the
        tier workflow again, so we clear `invoice_payment_review_state_manual`.
        """

        res = super(AccountMove, self).restart_validation()
        for move in self:
            if move.invoice_payment_review_state_manual:
                move.invoice_payment_review_state_manual = False

        return res

    def write(self, vals):
        """
        When a manual payment review state is set, align tier reviews accordingly.

        - to_review / not_required: remove all existing reviews.
        - approved: keep only validated reviews.
        - declined: keep only rejected reviews.

        This keeps the tier validation history consistent with the manual override.
        """

        new_state = vals.get('invoice_payment_review_state_manual')
        res = super().write(vals)

        if not new_state:
            return res

        reviews = self.mapped('review_ids')
        if not reviews:
            return res

        if new_state in {'to_review', 'not_required'}:
            reviews.unlink()
            return res

        keep_status = 'validated' if new_state == 'approved' else 'rejected'

        to_unlink = reviews.filtered(lambda r: r.status != keep_status)
        if to_unlink:
            to_unlink.unlink()

        return res

    def _payment_validation_required(self):
        self.ensure_one()
        return (
            not self.is_intragroup_invoice
            and self._is_vendor_bill_posted()
        )

    def _is_vendor_bill_posted(self):
        self.ensure_one()
        return self.state == 'posted' and self.move_type in ('in_invoice', 'in_refund')

    def _get_under_validation_exceptions(self):
        return (super()._get_under_validation_exceptions() + [
            'needed_terms_dirty',
            'checked',
            'state',
            'invoice_payment_review_state_manual'
        ])

    def _get_after_validation_exceptions(self):
        return super()._get_after_validation_exceptions() + [
            'invoice_payment_review_state_manual',
            'extract_status',
            'posted_before',
            'state']

    def _get_validation_exceptions(self, extra_domain=None, add_base_exceptions=True):
        res = super()._get_validation_exceptions(extra_domain, add_base_exceptions)

        am_exceptions = [
            'amount_total',
            'needed_terms_dirty',
            'is_manually_modified',
            'is_move_sent',
            'sending_data',
            'matched_payment_ids',
            'payment_state',
            'invoice_payment_review_state',
        ]
        return res + am_exceptions
