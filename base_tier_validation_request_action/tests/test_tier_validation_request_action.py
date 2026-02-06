# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation


@tagged("post_install", "-at_install")
class TestTierValidationRequestAction(CommonTierValidation):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tier_def_obj = cls.env["tier.definition"]

        # Create test users
        cls.test_user_1 = cls.env["res.users"].create(
            {
                "name": "Test User 1",
                "login": "test_user_1",
                "email": "test1@test.com",
            }
        )
        cls.test_user_2 = cls.env["res.users"].create(
            {
                "name": "Test User 2",
                "login": "test_user_2",
                "email": "test2@test.com",
            }
        )

        # Create base tier definition
        cls.tier_def = cls.tier_def_obj.create(
            {
                "model_id": cls.tester_model.id,
                "review_type": "individual",
                "reviewer_id": cls.test_user_1.id,
                "definition_domain": "[('test_field', '>', 1.0)]",
            }
        )

        # Create test record
        cls.test_record = cls.test_model.create({"test_field": 2.5})

    def test_01_no_constraint(self):
        """Test validation request without constraint (default behavior)."""
        # constraint_type = 'none' by default
        reviews = self.test_record.with_user(self.test_user_2.id).request_validation()
        self.assertTrue(reviews)
        self.assertEqual(len(reviews), 1)

    def test_02_block_constraint(self):
        """Test block constraint - raises ValidationError."""
        self.tier_def.write(
            {
                "constraint_type": "block",
                "constraint_message": "This operation is blocked for testing",
            }
        )

        # Should raise ValidationError
        with self.assertRaises(ValidationError) as ctx:
            self.test_record.with_user(self.test_user_2.id).request_validation()

        self.assertIn("This operation is blocked", str(ctx.exception))

    def test_03_warning_constraint(self):
        """Test warning constraint - raises UserError."""
        self.tier_def.write(
            {
                "constraint_type": "warning",
                "constraint_message": "Warning: please review this carefully",
            }
        )

        # Should raise UserError
        with self.assertRaises(UserError) as ctx:
            self.test_record.with_user(self.test_user_2.id).request_validation()

        self.assertIn("Warning: please review", str(ctx.exception))

    def test_04_server_action_constraint(self):
        """Test server action constraint."""
        # Create a simple server action
        server_action = self.env["ir.actions.server"].create(
            {
                "name": "Test Constraint Action",
                "model_id": self.tester_model.id,
                "state": "code",
                "code": "record.write({'test_field': record.test_field + 10})",
            }
        )

        self.tier_def.write(
            {
                "constraint_type": "server_action",
                "constraint_server_action_id": server_action.id,
            }
        )

        original_value = self.test_record.test_field

        # Should execute server action and continue
        reviews = self.test_record.with_user(self.test_user_2.id).request_validation()

        self.assertTrue(reviews)
        # Server action should have been executed
        self.assertEqual(self.test_record.test_field, original_value + 10)

    def test_05_constraint_only_on_applicable_tier(self):
        """Test that constraint is only checked when tier applies."""
        # Change definition_domain so tier doesn't apply
        self.tier_def.write(
            {
                "definition_domain": "[('test_field', '<', 1.0)]",  # Won't match
                "constraint_type": "block",
                "constraint_message": "Should not be raised",
            }
        )

        # Should work because tier doesn't apply
        result = self.test_record.with_user(self.test_user_2.id).request_validation()
        self.assertIsNotNone(result)

    def test_06_multiple_tiers_with_constraints(self):
        """Test multiple tier definitions with different constraints."""
        # First tier: warning
        self.tier_def.write(
            {
                "constraint_type": "warning",
                "constraint_message": "First tier warning",
            }
        )

        # Second tier: block (will be checked first due to sequence)
        tier_def_2 = self.tier_def_obj.create(
            {
                "model_id": self.tester_model.id,
                "review_type": "individual",
                "reviewer_id": self.test_user_2.id,
                "definition_domain": "[('test_field', '>', 2.0)]",
                "constraint_type": "block",
                "constraint_message": "Second tier blocks",
                "sequence": 1,  # Lower sequence = checked first
            }
        )

        # Should raise error from first constraint checked (lowest sequence)
        with self.assertRaises(ValidationError) as ctx:
            self.test_record.with_user(self.test_user_2.id).request_validation()

        self.assertIn("Second tier blocks", str(ctx.exception))

    def test_07_default_message_if_not_set(self):
        """Test that default message is used if constraint_message is empty."""
        self.tier_def.write(
            {
                "constraint_type": "block",
                "constraint_message": False,  # No custom message
            }
        )

        # Should raise ValidationError with default message
        with self.assertRaises(ValidationError) as ctx:
            self.test_record.with_user(self.test_user_2.id).request_validation()

        # Default message should contain tier name or reference
        self.assertIn("Constraint failed", str(ctx.exception))

    def test_08_server_action_without_action_configured(self):
        """Test server_action type without action configured."""
        self.tier_def.write(
            {
                "constraint_type": "server_action",
                "constraint_server_action_id": False,  # No action
            }
        )

        # Should continue without error (just logs warning)
        reviews = self.test_record.with_user(self.test_user_2.id).request_validation()
        self.assertTrue(reviews)
