# Copyright <2020> PESOL <info@pesol.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "tier.validation"]
    _state_from = ["draft"]
    _state_to = ["posted"]

    _tier_validation_manual_config = False

    @api.depends("need_validation")
    def _compute_hide_post_button(self):
        result = super()._compute_hide_post_button()
        for this in self:
            this.hide_post_button |= this.need_validation
        return result

    def _get_under_validation_exceptions(self):
        return super()._get_under_validation_exceptions() + ["needed_terms_dirty"]

    def _get_validation_exceptions(self, extra_domain=None, add_base_exceptions=True):
        res = super()._get_validation_exceptions(extra_domain, add_base_exceptions)
        # we need to exclude amount_total,
        # otherwise editing manually the values on lines dirties the field at onchange
        # since it's not in readonly because readonly="not(review_ids)", it's then
        # sent at save, and will override the values set by the user
        # The other exclusions are needed to be able to generate the pdf
        # and send the invoice by email
        am_exceptions = [
            "amount_total",
            "needed_terms_dirty",
            "is_manually_modified",
            "is_move_sent",
            "sending_data",
            "matched_payment_ids",
            "payment_state",
        ]
        return res + am_exceptions + self._get_ocr_exception_fields()

    def _get_ocr_exception_fields(self):
        """Fields of the bill digitization (OCR) of Odoo Enterprise.

        Its scheduled actions write the OCR status of a bill also while it
        is under review, and once it is posted. Without these, the action
        that reports the posted bills back to the OCR service fails on the
        first bill that went through a review, and so for all bills.
        These fields only exist with Enterprise; without it this is empty.
        """
        return [name for name in self._fields if name.startswith("extract_")]

    def _get_to_validate_message_name(self):
        name = super()._get_to_validate_message_name()
        if self.move_type == "in_invoice":
            name = self.env._("Bill")
        elif self.move_type == "in_refund":
            name = self.env._("Refund")
        elif self.move_type == "out_invoice":
            name = self.env._("Invoice")
        elif self.move_type == "out_refund":
            name = self.env._("Credit Note")
        return name

    def action_post(self):
        return super(
            AccountMove, self.with_context(skip_validation_check=True)
        ).action_post()
