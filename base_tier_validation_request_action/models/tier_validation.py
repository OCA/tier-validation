# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    def _get_applicable_tier_definitions_with_constraints(self):
        """Get tier definitions that apply to this record and have constraints."""
        self.ensure_one()
        td_obj = self.env["tier.definition"]
        tier_definitions = td_obj.search(
            [
                ("model", "=", self._name),
                ("company_id", "in", [False] + self._get_company().ids),
                ("constraint_type", "!=", "none"),
            ],
            order="sequence asc",
        )
        # Filter only tiers that apply to this record
        return tier_definitions.filtered(lambda td: self.evaluate_tier(td))

    def _process_tier_constraint(self, tier_definition):
        """Process tier definition constraint on validation request.

        Raise errors or execute actions based on constraint type.
        """
        self.ensure_one()

        constraint_type = tier_definition.constraint_type

        if constraint_type == "none":
            return

        tier_name = tier_definition.name or _("Tier %s", tier_definition.sequence)
        message = tier_definition.constraint_message or _(
            "Constraint failed for tier: %(tier)s", tier=tier_name
        )

        if constraint_type == "block":
            # Raise ValidationError - blocks the validation request
            raise ValidationError(
                _("%(tier)s: %(message)s", tier=tier_name, message=message)
            )

        elif constraint_type == "warning":
            # Raise UserError - shows warning to user
            raise UserError(_("%(tier)s: %(message)s", tier=tier_name, message=message))

        elif constraint_type == "server_action":
            # Execute server action
            server_action = tier_definition.constraint_server_action_id
            if not server_action:
                _logger.warning(
                    "Tier definition %s has constraint_type='server_action' "
                    "but no server action configured",
                    tier_definition.name,
                )
                return

            # Prevent reentrant execution
            constraint_action_tier = self.env.context.get("constraint_action_tier")
            if (
                not constraint_action_tier
                or constraint_action_tier != server_action.id
            ):
                try:
                    server_action.with_context(
                        constraint_action_tier=server_action.id,
                        active_model=self._name,
                        active_id=self.id,
                        active_ids=self.ids,
                    ).sudo().run()
                    _logger.info(
                        "Executed server action '%s' for tier constraint on %s (ID: %s)",
                        server_action.name,
                        self._name,
                        self.id,
                    )
                except Exception as e:
                    _logger.error(
                        "Error executing server action '%s' for tier: %s",
                        server_action.name,
                        str(e),
                    )
                    # Optionally re-raise the error
                    raise

    def request_validation(self):
        """Override to check constraints before allowing validation request."""
        # Check constraints for each record
        for rec in self:
            if rec._check_state_from_condition() and rec.need_validation:
                tier_definitions = rec._get_applicable_tier_definitions_with_constraints()
                for tier_def in tier_definitions:
                    # This will raise an error if constraint type is block/warning
                    rec._process_tier_constraint(tier_def)

        # Call parent to create reviews if no errors were raised
        return super().request_validation()
