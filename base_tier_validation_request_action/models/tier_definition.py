# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    # Constraint type - what to do when tier applies
    constraint_type = fields.Selection(
        [
            ("none", "No Constraint"),
            ("block", "Block (ValidationError)"),
            ("warning", "Warning (UserError)"),
            ("server_action", "Execute Server Action"),
        ],
        string="Constraint Type",
        default="none",
        help="Action to trigger when validation is requested:\n"
        "- No Constraint: Do nothing (default behavior)\n"
        "- Block: Raise ValidationError and prevent validation request\n"
        "- Warning: Raise UserError with warning message\n"
        "- Execute Server Action: Run a server action",
    )

    # Error/warning message
    constraint_message = fields.Text(
        string="Constraint Message",
        help="Message to display when constraint is triggered. "
        "Used for Block and Warning types.",
    )

    # Server action to execute
    constraint_server_action_id = fields.Many2one(
        comodel_name="ir.actions.server",
        string="Server Action",
        domain=[("usage", "=", "ir_actions_server")],
        help="Server action to execute when validation is requested "
        "(only used when Constraint Type is 'Execute Server Action').",
    )
