# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests.common import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestPurchaseBridgeExceptions(BaseCommon):
    """Verify the bridge adds the purchase-reconcile fields to the
    tier-validation exception list on ``account.move``.

    The behavioural test (auto-complete a validated bill from a PO and
    confirm the lines actually get copied) is end-to-end and lives in
    the purchase + tier-validation integration suites in the customer
    project. Here we keep a focused module-level check: the fields are
    present in ``_get_validation_exceptions`` whenever both modules are
    installed.
    """

    def test_purchase_fields_in_exceptions(self):
        exceptions = self.env["account.move"]._get_validation_exceptions()
        for field_name in (
            "purchase_vendor_bill_id",
            "purchase_id",
            "invoice_vendor_bill_id",
            "invoice_origin",
            "invoice_line_ids",
            "line_ids",
        ):
            self.assertIn(
                field_name,
                exceptions,
                f"Field {field_name!r} must be exempt from the "
                f"tier-validation lock so the Reconcile-with-PO flow "
                f"works on validated bills.",
            )
