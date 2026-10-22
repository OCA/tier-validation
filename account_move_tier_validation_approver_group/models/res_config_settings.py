# Copyright 2020 ForgeFlow, S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    require_approver_group_in_vendor_bills = fields.Boolean(
        string="Require Approver Group In Vendor Bills",
        help="Requires adding an approver group before a vendor bill can be posted. "
        "Note: If you combine both rules, be sure to configure the appropriate domains "
        "on the tier definitions",
        related="company_id.require_approver_group_in_vendor_bills",
        readonly=False,
    )

    def set_values(self):
        company = self.company_id
        tier_definition = company.validation_approver_group_tier_definition_id
        if not tier_definition:
            field = self.env["ir.model.fields"]._get(
                "account.move", "approver_group_id"
            )
            tier_definition = self.env["tier.definition"].create(
                self._prepare_tier_approver_group_definition_values(field)
            )
            company.validation_approver_group_tier_definition_id = tier_definition
        if self.require_approver_group_in_vendor_bills:
            tier_definition.action_unarchive()
        else:
            tier_definition.action_archive()
        return super().set_values()

    def _prepare_tier_approver_group_definition_values(self, field):
        return {
            "model_id": self.env["ir.model"]._get_id("account.move"),
            "review_type": "field",
            "name": "Validation with Approver field (group)",
            "reviewer_field_id": field.id,
            "definition_domain": (
                "[('move_type', '=', 'in_invoice'), ('approver_group_id', '!=', False)]"
            ),
            "approve_sequence": True,
            "active": self.require_approver_group_in_vendor_bills,
        }
