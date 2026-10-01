# Copyright 2026 bosd
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    contract_lock_lines_after_validation = fields.Boolean(
        related="company_id.contract_lock_lines_after_validation",
        readonly=False,
    )
