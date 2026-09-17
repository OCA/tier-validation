# Copyright 2021 ForgeFlow (http://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import new_test_user, tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestAccountMoveTierValidationApprover(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.res_partner_1 = cls.env["res.partner"].create(
            {"name": "Wood Corner", "email": "example@yourcompany.com"}
        )
        cls.product_1 = cls.env["product.product"].create({"name": "Desk Combination"})
        cls.currency_usd = cls.env["res.currency"].search([("name", "=", "USD")])
        cls.test_user_1 = new_test_user(
            cls.env,
            login="test1",
            email="example@yourcompany.com",
            groups="base.group_system,account.group_account_manager",
        )
        cls.test_approver = new_test_user(
            cls.env,
            login="test2",
            email="example@yourcompany.com",
            groups="base.group_system,account.group_account_manager",
        )
        cls.vendor_bill = cls.env["account.move"].create(
            [
                {
                    "move_type": "in_invoice",
                    "partner_id": cls.res_partner_1.id,
                    "currency_id": cls.currency_usd.id,
                    "approver_id": cls.test_approver.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": cls.product_1.id,
                                "product_uom_id": cls.product_1.uom_id.id,
                                "quantity": 12,
                                "price_unit": 1000,
                            },
                        ),
                    ],
                }
            ]
        )
        cls.model_id = cls.env["ir.model"].search(
            [("model", "=", "account.move")], limit=1
        )
        cls.field_id = cls.env["ir.model.fields"].search(
            [("name", "=", "approver_id")], limit=1
        )

    def test_field_validation_approver(self):
        tiers = self.env["tier.definition"].search([])
        for tier in tiers:
            tier.action_archive()
        self.tier_definition = self.env["tier.definition"].create(
            {
                "name": "Test Tier",
                "model_id": self.model_id.id,
                "review_type": "field",
                "reviewer_field_id": self.field_id.id,
                "definition_type": "domain",
                "definition_domain": "[('move_type', '=', 'in_invoice')]",
            }
        )
        record = self.vendor_bill
        record.write(
            {"approver_id": self.test_approver.id, "invoice_date": record.date}
        )
        record.with_user(self.test_user_1.id).request_validation()
        record.with_user(self.test_user_1.id).validate_tier()
        with self.assertRaises(ValidationError):
            record.action_post()
        record.with_user(self.test_approver.id).validate_tier()
        record.action_post()
