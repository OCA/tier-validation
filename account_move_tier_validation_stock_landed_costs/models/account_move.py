# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_validation_exceptions(self, extra_domain=None, add_base_exceptions=True):
        """Allow the *Create Landed Costs* flow on validated bills.

        ``stock_landed_costs`` adds the *Create Landed Costs* button
        whose visibility depends on at least one move line having
        ``is_landed_costs_line=True``. The user typically toggles that
        flag (via the *Landed Costs* product or the line's own
        checkbox) AFTER the bill exists but BEFORE invoicing fires
        the landed-cost split.

        Once ``validation_status='validated'`` the line-level edits
        are blocked by the tier-validation lock. Add the relevant
        fields to the exception list so:

        - ``invoice_line_ids`` / ``line_ids`` stay editable on a
          validated bill (the user can mark a line as a landed-cost
          line, which feeds ``_compute_landed_costs_visible`` and
          re-enables the button).
        - ``landed_costs_ids`` (the One2many to ``stock.landed.cost``
          on the bill) is exempt as well, although in practice the
          button creates the related record on a separate model so
          this is defensive.
        """
        res = super()._get_validation_exceptions(
            extra_domain=extra_domain,
            add_base_exceptions=add_base_exceptions,
        )
        return res + [
            "invoice_line_ids",
            "line_ids",
            "landed_costs_ids",
        ]
