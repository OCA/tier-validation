# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_validation_exceptions(self, extra_domain=None, add_base_exceptions=True):
        """Allow the *Reconcile with Purchase Order* flow on validated bills.

        The Auto-complete picker on a vendor bill works by writing the
        non-stored ``purchase_vendor_bill_id`` / ``purchase_id`` fields,
        which trigger an onchange that copies lines from the picked PO
        and updates ``invoice_origin`` / ``invoice_vendor_bill_id`` /
        ``invoice_line_ids``. Without these fields in the validation-
        exception list:

        - The auto-complete pickers themselves are rendered readonly by
          ``base_tier_validation``'s view post-processing once
          ``validation_status`` is anything but ``no``, so the user
          cannot even open the picker.
        - The onchange-driven write of ``invoice_line_ids`` / origin
          would be refused by ``_tier_validation_check_write_allowed``
          on any record that has a ``tier.validation.exception`` set,
          even a different one.

        Expose those fields explicitly so a bill can still be matched
        against a PO after validation -- the typical workflow when a
        purchasing user pre-validates a bill and a finance user then
        attaches the matching PO.
        """
        res = super()._get_validation_exceptions(
            extra_domain=extra_domain,
            add_base_exceptions=add_base_exceptions,
        )
        return res + [
            "purchase_vendor_bill_id",
            "purchase_id",
            "invoice_vendor_bill_id",
            "invoice_origin",
            "invoice_line_ids",
            "line_ids",
        ]
