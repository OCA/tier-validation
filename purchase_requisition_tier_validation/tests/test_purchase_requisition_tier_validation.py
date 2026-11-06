# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests import common


class TestPurchaseRequisitionTierValidation(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tier_definition = cls.env["tier.definition"]

    def test_get_tier_validation_model_names(self):
        self.assertIn(
            "purchase.requisition",
            self.tier_definition._get_tier_validation_model_names(),
        )

    def test_purchase_requisition_tier_validation_enforced(self):
        """Confirming a requisition under validation must be blocked until
        the tier review passes, and allowed once it does.

        This specifically exercises '_state_to = ["confirmed"]': if that
        value did not match the real v19 core state used by action_confirm,
        the mixin's write() interception would never trigger and this test
        would fail to raise on the first action_confirm() call.
        """
        reviewer = self.env["res.users"].create(
            {
                "name": "Test PA Reviewer",
                "login": "test_pa_reviewer",
                "email": "test_pa_reviewer@example.com",
            }
        )
        vendor = self.env["res.partner"].create({"name": "Test PA Vendor"})
        product = self.env["product.product"].create(
            {"name": "Test PA Product", "purchase_ok": True}
        )
        self.tier_definition.create(
            {
                "definition_domain": "[]",
                "model_id": self.env["ir.model"]._get("purchase.requisition").id,
                "review_type": "individual",
                "reviewer_id": reviewer.id,
            }
        )
        requisition = self.env["purchase.requisition"].create(
            {
                "vendor_id": vendor.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": 1,
                            "price_unit": 10.0,
                        },
                    ),
                ],
            }
        )
        self.assertEqual(requisition.state, "draft")

        with self.assertRaisesRegex(ValidationError, "validated"):
            with self.env.cr.savepoint():
                requisition.action_confirm()

        requisition.request_validation()
        requisition.review_ids.invalidate_recordset()
        self.assertEqual(requisition.validation_status, "pending")

        requisition.with_user(reviewer).validate_tier()
        requisition.invalidate_recordset()
        self.assertEqual(requisition.validation_status, "validated")

        requisition.action_confirm()
        self.assertEqual(requisition.state, "confirmed")
