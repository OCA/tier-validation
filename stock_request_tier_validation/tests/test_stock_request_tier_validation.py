# Copyright 2026 Jarsa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestStockRequestTierValidation(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.test_user = new_test_user(
            cls.env,
            name="Test Reviewer",
            login="test_reviewer",
            groups="base.group_system,stock_request.group_stock_request_manager",
        )
        cls.env["tier.definition"].create(
            {
                "model_id": cls.env.ref("stock_request.model_stock_request").id,
                "review_type": "individual",
                "reviewer_id": cls.test_user.id,
                "definition_domain": (
                    "[('state', '=', 'draft'), ('order_id', '=', False)]"
                ),
            }
        )
        cls.env["tier.definition"].create(
            {
                "model_id": cls.env.ref("stock_request.model_stock_request_order").id,
                "review_type": "individual",
                "reviewer_id": cls.test_user.id,
                "definition_domain": "[('state', '=', 'draft')]",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "type": "consu",
                "is_storable": True,
            }
        )
        cls.ressuply_loc = cls.env["stock.location"].create(
            {
                "name": "Ressuply",
                "usage": "internal",
                "location_id": cls.warehouse.view_location_id.id,
                "company_id": cls.company.id,
            }
        )
        cls.route = cls.env["stock.route"].create(
            {
                "name": "Transfer",
                "product_selectable": True,
                "company_id": cls.company.id,
                "rule_ids": [
                    Command.create(
                        {
                            "name": "Transfer",
                            "location_src_id": cls.ressuply_loc.id,
                            "location_dest_id": cls.warehouse.lot_stock_id.id,
                            "action": "pull",
                            "picking_type_id": cls.warehouse.int_type_id.id,
                            "procure_method": "make_to_stock",
                            "warehouse_id": cls.warehouse.id,
                            "company_id": cls.company.id,
                        }
                    )
                ],
            }
        )
        cls.product.route_ids = [Command.set(cls.route.ids)]

    def test_tier_validation(self):
        request = self.env["stock.request"].create(
            {
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "product_uom_qty": 5.0,
                "company_id": self.company.id,
                "warehouse_id": self.warehouse.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "expected_date": fields.Datetime.now(),
            }
        )
        msg_error_received = (
            r"(?s)This action needs to be validated for at least one record\..*"
            r"Please request a validation\."
        )
        with self.assertRaisesRegex(ValidationError, msg_error_received):
            request.action_confirm()
        request.request_validation()
        request.invalidate_model()
        msg_error_open = (
            r"(?s)A validation process is still open for at least one record\."
        )
        with self.assertRaisesRegex(ValidationError, msg_error_open):
            request.action_confirm()
        request.with_user(self.test_user).validate_tier()
        request.invalidate_model()
        request.action_confirm()
        self.assertEqual(request.state, "open")
        self.assertEqual(request.validation_status, "validated")

    def test_tier_validation_order(self):
        order = self.env["stock.request.order"].create(
            {
                "company_id": self.company.id,
                "warehouse_id": self.warehouse.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "expected_date": fields.Datetime.now(),
                "stock_request_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_id": self.product.uom_id.id,
                            "product_uom_qty": 5.0,
                            "company_id": self.company.id,
                            "warehouse_id": self.warehouse.id,
                            "location_id": self.warehouse.lot_stock_id.id,
                            "expected_date": fields.Datetime.now(),
                        }
                    )
                ],
            }
        )
        msg_error_received = (
            r"(?s)This action needs to be validated for at least one record\..*"
            r"Please request a validation\."
        )
        with self.assertRaisesRegex(ValidationError, msg_error_received):
            order.action_confirm()
        order.request_validation()
        order.invalidate_model()
        msg_error_open = (
            r"(?s)A validation process is still open for at least one record\."
        )
        with self.assertRaisesRegex(ValidationError, msg_error_open):
            order.action_confirm()
        order.with_user(self.test_user).validate_tier()
        order.invalidate_model()
        order.action_confirm()
        self.assertEqual(order.state, "open")
        self.assertEqual(order.validation_status, "validated")
