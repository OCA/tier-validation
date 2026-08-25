# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests.common import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestLandedCostsBridgeExceptions(BaseCommon):
    """Verify the bridge adds the landed-cost-related fields to the
    tier-validation exception list on ``account.move``.
    """

    def test_landed_costs_fields_in_exceptions(self):
        exceptions = self.env["account.move"]._get_validation_exceptions()
        for field_name in (
            "invoice_line_ids",
            "line_ids",
            "landed_costs_ids",
        ):
            self.assertIn(
                field_name,
                exceptions,
                f"Field {field_name!r} must be exempt from the "
                f"tier-validation lock so the Create-Landed-Costs flow "
                f"works on validated bills.",
            )
