# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    allow_multi_validate = fields.Boolean(
        string="Allow Multi Validation",
        help="Add the Request Validation, Validate and Reject buttons to the list "
        "and kanban views of this model, shown when records are selected. Only "
        "the reviews of definitions with this option are validated or rejected "
        "from there. Reload the browser after changing it.",
    )
