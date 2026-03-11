# Copyright 2025 Scalizer (<https://www.scalizer.fr>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "tier.validation"]

    _tier_validation_buttons_xpath = "/form/header/field[@name='state']"
    _state_from = ["draft"]
    _state_to = ["active"]
    _cancel_state = ["archived"]
    _tier_validation_manual_config = False

    def write(self, vals):
        # Tier Validation works with state (char), synced from product_state_id
        if "product_state_id" in vals:
            state_id = vals.get("product_state_id")
            state = self.env["product.state"].browse(state_id)
            vals["state"] = state.code
        res = super().write(vals)
        return res