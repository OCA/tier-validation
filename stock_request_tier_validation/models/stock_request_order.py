# Copyright 2026 Jarsa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import ValidationError


class StockRequestOrder(models.Model):
    _name = "stock.request.order"
    _inherit = ["stock.request.order", "tier.validation"]
    _state_from = ["draft"]
    _state_to = ["open"]

    _tier_validation_manual_config = False
    # state is a stored computed field on stock.request.order
    _tier_validation_state_field_is_computed = True

    def action_confirm(self):
        # state is computed and flushed lazily, so validate explicitly
        # before confirming instead of relying on the write() check
        for rec in self:
            if rec.need_validation:
                reviews = rec.request_validation()
                rec._validate_tier(reviews)
                if rec.validation_status != "validated":
                    raise ValidationError(
                        self.env._(
                            "This action needs to be validated for at least "
                            "one record. \nPlease request a validation."
                        )
                    )
            if rec.review_ids and rec.validation_status != "validated":
                raise ValidationError(
                    self.env._(
                        "A validation process is still open for at least one record."
                    )
                )
        return super().action_confirm()
