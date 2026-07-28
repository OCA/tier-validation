# Copyright 2026 Jarsa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class StockRequest(models.Model):
    _name = "stock.request"
    _inherit = ["stock.request", "tier.validation"]
    _state_from = ["draft"]
    _state_to = ["open"]

    _tier_validation_manual_config = False
