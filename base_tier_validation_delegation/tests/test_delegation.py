# Copyright 2025 360ERP (<https://www.360erp.com>)
# Copyright 2026 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from datetime import date, timedelta

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import tagged

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation
import logging
_logger = logging.getLogger(__name__)

@tagged("post_install", "-at_install")
class TestTierValidationDelegation(CommonTierValidation):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_delegator = cls.test_user_1
        cls.user_replacer_b = cls.env["res.users"].create(
            {"name": "User B (Replacer)", "login": "user_b", "email": "b@test.com"}
        )
        cls.user_replacer_c = cls.env["res.users"].create(
            {"name": "User C (Final)", "login": "user_c", "email": "c@test.com"}
        )
        cls.admin_user = cls.env["res.users"].create(
            {"name": "Delegation Admin", "login": "deleg_admin", "email": "da@test.com"}
        )
        cls.delegation_admin_group = cls.env.ref(
            "base_tier_validation_delegation.group_delegation_administrator"
        )
        cls.admin_user.write({"group_ids": [(4, cls.delegation_admin_group.id)]})

        cls.test_group = cls.env["res.groups"].create({"name": "Test Review Group"})
        cls.test_user_1.write({"group_ids": [(4, cls.test_group.id)]})
        cls.test_user_2.write({"group_ids": [(4, cls.test_group.id)]})
        cls.tier_def = cls.env["tier.definition"].create(
            {
                "model_id": cls.tester_model.id,
                "approve_sequence": False,
                "review_type": "individual",
                "reviewer_id": cls.user_delegator.id,
                "definition_domain": "[('test_field', '>', 1.0)]",
            }
        )

    def tearDown(self):
        super().tearDown()
        users_to_reset = (
            self.user_delegator
            | self.user_replacer_b
            | self.user_replacer_c
            | self.test_user_2
        )
        users_to_reset.write(
            {"on_holiday": False, "validation_replacer_id": False, "active": True}
        )


    def _create_record_and_request_validation(self, test_field_value=2.5):
        record = self.test_model.create({"test_field":test_field_value})
        record.with_user(self.test_user_2.id).request_validation()
        reviews = record.review_ids
        self.assertTrue(reviews, "HELPER: Failed to create any tier reviews.")
        return record,reviews

    def test_01_new_validation_delegation(self):
        """Test that a new validation is immediately delegated."""
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        _record, review = self._create_record_and_request_validation()
        self.assertIn(self.user_replacer_b, review.reviewer_ids)
        self.assertNotIn(self.user_delegator, review.reviewer_ids)

    def test_02_pending_validation_delegation(self):
        """Test that a pending validation is re-assigned when a user goes on holiday."""
        _record,review = self._create_record_and_request_validation()
        self.assertIn(self.user_delegator, review.reviewer_ids)
        review._compute_can_review()

        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        self.env.flush_all()
        self.assertEqual(review.status, "pending")
        self.assertIn(self.user_replacer_b, review.reviewer_ids)
        self.assertNotIn(self.user_delegator, review.reviewer_ids)



    def test_03_delegation_with_date_range(self):
        """Test that delegation only occurs within the specified date range."""
        today = date.today()
        self.user_delegator.write(
            {
                "on_holiday": True,
                "holiday_start_date": today + timedelta(days=5),
                "validation_replacer_id": self.user_replacer_b.id,
            }
        )
        _record, review = self._create_record_and_request_validation()
        self.assertIn(
            self.user_delegator,
            review.reviewer_ids,
            "Review should not be delegated before the holiday start date.",
        )
        self.user_delegator.holiday_start_date = today - timedelta(days=1)
        review._compute_reviewer_ids()
        self.assertIn(
            self.user_replacer_b,
            review.reviewer_ids,
            "Review should be delegated once within the holiday period.",
        )

    def test_04_delegation_chain(self):
        """Test that a review is delegated to the end of a chain (A->B->C)."""
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        self.user_replacer_b.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_c.id}
        )
        _record, review = self._create_record_and_request_validation()
        self.assertIn(self.user_replacer_c, review.reviewer_ids)
        self.assertNotIn(self.user_delegator, review.reviewer_ids)
        self.assertNotIn(self.user_replacer_b, review.reviewer_ids)

    def test_05_group_review_delegation(self):
        """Test delegation for a review assigned to a group where one member is away."""
        group_tier_def = self.env["tier.definition"].create(
            {
                "model_id": self.tester_model.id,
                "review_type": "group",
                "reviewer_group_id": self.test_group.id,
            }
        )
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_c.id}
        )
        _record, reviews = self._create_record_and_request_validation(
            test_field_value=0.5
        )
        review = reviews.filtered(lambda r: r.definition_id == group_tier_def)
        self.assertTrue(review)
        self.assertIn(self.test_user_2, review.reviewer_ids)
        self.assertIn(self.user_replacer_c, review.reviewer_ids)
        self.assertNotIn(self.user_delegator, review.reviewer_ids)

    def test_06_user_returns_from_holiday_default(self):
        """Test that pending reviews are reassigned back when a user returns."""
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )

        _record_while_away, review_while_away = self._create_record_and_request_validation()

        # Make test deterministic: ensure the review is actually pending
        review_while_away._compute_can_review()
        self.env.flush_all()
        review_while_away.invalidate_recordset(
            ["status", "reviewer_ids", "delegated_by_ids"])
        review_while_away = self.env["tier.review"].browse(review_while_away.id)

        self.assertEqual(review_while_away.status, "pending")
        self.assertIn(self.user_replacer_b, review_while_away.reviewer_ids)

        # User returns
        self.user_delegator.write({"on_holiday": False})

        self.env.flush_all()
        review_while_away.invalidate_recordset(
            ["status", "reviewer_ids", "delegated_by_ids"])
        review_while_away = self.env["tier.review"].browse(review_while_away.id)

        self.assertIn(
            self.user_delegator,
            review_while_away.reviewer_ids,
            "Pending review should be reassigned back to the original user.",
        )
        self.assertNotIn(
            self.user_replacer_b,
            review_while_away.reviewer_ids,
            "Replacer should be removed after the original user returns.",
        )

        _record_after_return, review_after_return = self._create_record_and_request_validation()
        review_after_return._compute_can_review()
        self.env.flush_all()
        review_after_return.invalidate_recordset(["status", "reviewer_ids"])
        review_after_return = self.env["tier.review"].browse(review_after_return.id)

        self.assertEqual(review_after_return.status, "pending")
        self.assertIn(self.user_delegator, review_after_return.reviewer_ids)

    def test_07_no_replacer_configured(self):
        """Test that if 'On Holiday' is checked with no replacer, delegation does not occur."""
        self.user_delegator.write({"on_holiday": True, "validation_replacer_id": False})
        _record, review = self._create_record_and_request_validation()
        self.assertIn(self.user_delegator, review.reviewer_ids)

    def test_08_self_delegation_constraint(self):
        """Test that a user cannot delegate to themselves."""
        with self.assertRaises(
            ValidationError, msg="Should not be able to delegate to self."
        ):
            self.user_delegator.write(
                {
                    "on_holiday": True,
                    "validation_replacer_id": self.user_delegator.id,
                }
            )

    def test_10_visual_indicator_and_menu(self):
        """Test that `delegated_by_ids` is set and the menu domain works."""
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        _record, review = self._create_record_and_request_validation()
        self.assertEqual(review.delegated_by_ids, self.user_delegator)
        delegated_reviews = (
            self.env["tier.review"]
            .with_user(self.user_delegator)
            .search([("delegated_by_ids", "in", [self.user_delegator.id])])
        )
        self.assertEqual(review, delegated_reviews)

    def test_11_admin_management(self):
        """Test that an admin can edit others' settings, but a normal user cannot."""
        with self.assertRaises(
            AccessError,
            msg="Normal user should not be able to edit other users' delegation.",
        ):
            self.user_delegator.with_user(self.test_user_2).write({"on_holiday": True})
        self.user_delegator.with_user(self.user_delegator).write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        self.user_delegator.with_user(self.admin_user).write(
            {"on_holiday": False, "validation_replacer_id": False}
        )

    def test_12_cron_job(self):
        """Test the automatic activation/deactivation cron job."""
        today = date.today()
        user_to_activate = self.user_replacer_b
        user_to_deactivate = self.user_replacer_c
        user_to_activate.write(
            {
                "on_holiday": False,
                "holiday_start_date": today,
                "validation_replacer_id": self.user_delegator.id,
            }
        )
        user_to_deactivate.write(
            {"on_holiday": True, "holiday_end_date": today - timedelta(days=1)}
        )
        self.env["res.users"]._cron_update_holiday_status()
        self.assertTrue(user_to_activate.on_holiday)
        self.assertFalse(user_to_deactivate.on_holiday)

    def test_14_circular_delegation_constraint(self):
        """Test that a circular delegation (A->B->A) is prevented."""
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        with self.assertRaises(
            ValidationError, msg="Should not be able to create a delegation loop."
        ):
            self.user_replacer_b.write(
                {
                    "on_holiday": True,
                    "validation_replacer_id": self.user_delegator.id,
                }
            )

    def test_15_delegation_to_archived_user(self):
        """Test that delegation falls back to the original user if the replacer is archived."""
        self.user_replacer_b.action_archive()
        self.assertFalse(self.user_replacer_b.active)
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        _record, review = self._create_record_and_request_validation()
        self.assertIn(
            self.user_delegator,
            review.reviewer_ids,
            "Review should fall back to delegator if replacer is inactive.",
        )
        self.assertNotIn(self.user_replacer_b, review.reviewer_ids)

    def test_16_multi_tier_delegation(self):
        """Test that delegation works correctly in a multi-tier validation flow."""
        self.env["tier.definition"].create(
            {
                "model_id": self.tester_model.id,
                "review_type": "individual",
                "reviewer_id": self.user_replacer_c.id,
                "sequence": 40,
            }
        )
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        record, reviews = self._create_record_and_request_validation()

        tier1_review = reviews.filtered(
            lambda r: r.definition_id.reviewer_id == self.user_delegator
        )
        tier2_review = reviews.filtered(
            lambda r: r.definition_id.reviewer_id == self.user_replacer_c
        )

        self.assertIn(self.user_replacer_b, tier1_review.reviewer_ids)

        # Validate the first tier as the replacer
        record.with_user(self.user_replacer_b).validate_tier()

        # Invalidate cache to ensure we read the latest status
        tier1_review.invalidate_recordset(["status"])
        tier2_review.invalidate_recordset(["status"])

        self.assertEqual(tier1_review.status, "approved", "Tier 1 should be approved.")
        self.assertEqual(
            tier2_review.status, "pending", "Tier 2 should now be pending."
        )

    def test_17_delegation_by_field_reviewer(self):
        """
        Test Case for the Primary Fix.

        This test ensures that a pending review is correctly delegated when the
        reviewer was assigned via a dynamic field (`review_type` = 'field').
        """
        reviewer_field = self.env["ir.model.fields"].search(
            [
                ("model", "=", "tier.validation.tester"),
                ("name", "=", "user_id"),
            ],
            limit=1,
        )
        self.assertTrue(reviewer_field, "Setup failed: Could not find 'user_id' field.")

        field_tier_def = self.env["tier.definition"].create(
            {
                "model_id": self.tester_model.id,
                "review_type": "field",
                "reviewer_field_id": reviewer_field.id,
                "name": "Field-Based Review",
            }
        )

        record = self.test_model.create(
            {"test_field": 1.0, "user_id": self.user_delegator.id}
        )
        record.with_user(self.test_user_2).request_validation()

        review = self.env["tier.review"].search(
            [
                ("res_id", "=", record.id),
                ("definition_id", "=", field_tier_def.id),
                # Better to add:
                # ("model", "=", record._name),
            ],
            limit=1,
        )
        self.assertTrue(review, "Test setup failed: Review was not created.")

        # 1) Ensure it is pending BEFORE changing holiday status (pending-only rule)
        review._compute_can_review()
        self.env.flush_all()
        review.invalidate_recordset(["status", "reviewer_ids", "delegated_by_ids"])
        review = self.env["tier.review"].browse(review.id)

        self.assertEqual(review.status, "pending")
        self.assertIn(
            self.user_delegator,
            review.reviewer_ids,
            "Initial reviewer should be the user from the 'user_id' field.",
        )

        # 2) Action: go on holiday -> write() hook recomputes pending reviews
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )

        # 3) Assert
        self.env.flush_all()
        review.invalidate_recordset(["status", "reviewer_ids", "delegated_by_ids"])
        review = self.env["tier.review"].browse(review.id)

        self.assertEqual(review.status, "pending")
        self.assertIn(
            self.user_replacer_b,
            review.reviewer_ids,
            "Review should have been delegated to the replacer.",
        )
        self.assertNotIn(
            self.user_delegator,
            review.reviewer_ids,
            "Original reviewer should have been removed after delegation.",
        )

    def test_18_change_replacer_while_on_holiday(self):
        """
        Test Case for the Secondary Fix.

        This test ensures that if a user is already on holiday and their
        replacer is changed, their pending reviews are correctly moved from
        the old replacer to the new one.
        """
        # 1) Setup: delegator on holiday -> delegated to B
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        record, review = self._create_record_and_request_validation()

        # Make test deterministic: ensure the review is actually pending
        review._compute_can_review()
        self.env.flush_all()
        review.invalidate_recordset(["status", "reviewer_ids", "delegated_by_ids"])
        review = self.env["tier.review"].browse(review.id)

        self.assertEqual(review.status, "pending")
        self.assertIn(
            self.user_replacer_b,
            review.reviewer_ids,
            "Initial delegation to Replacer B should have occurred.",
        )
        self.assertNotIn(self.user_delegator, review.reviewer_ids)

        # 2) Action: still on holiday, change replacer B -> C
        self.user_delegator.write({"validation_replacer_id": self.user_replacer_c.id})

        # 3) Assert: review moved from B to C
        self.env.flush_all()
        review.invalidate_recordset(["status", "reviewer_ids", "delegated_by_ids"])
        review = self.env["tier.review"].browse(review.id)

        self.assertEqual(review.status, "pending")
        self.assertIn(
            self.user_replacer_c,
            review.reviewer_ids,
            "Review should have been re-delegated to the new replacer (C).",
        )
        self.assertNotIn(
            self.user_replacer_b,
            review.reviewer_ids,
            "The old replacer (B) should no longer be a reviewer.",
        )

    def test_19_return_from_holiday_reassigns_pending(self):
        """
        Test Case for returning from holiday.

        This test verifies the new behavior introduced by the fix: when a user
        returns from holiday (`on_holiday`=False), their pending reviews that
        were delegated are now reassigned back to them.
        """
        # 1. Setup: User is on holiday, and a review is delegated.
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        _record, review = self._create_record_and_request_validation()

        # IMPORTANT: make the test deterministic -> ensure review is pending
        review._compute_can_review()
        self.env.flush_all()
        review.invalidate_recordset(["status", "reviewer_ids", "delegated_by_ids"])
        review = self.env["tier.review"].browse(review.id)

        self.assertEqual(review.status, "pending")
        self.assertIn(
            self.user_replacer_b,
            review.reviewer_ids,
            "Review should be with the replacer while user is on holiday.",
        )

        # 2. Action: The user returns from holiday.
        self.user_delegator.write({"on_holiday": False})

        # 3. Assert: The pending review is reassigned back to the original user.
        self.env.flush_all()
        review.invalidate_recordset(["status", "reviewer_ids", "delegated_by_ids"])
        review = self.env["tier.review"].browse(review.id)

        self.assertEqual(review.status, "pending")
        self.assertIn(
            self.user_delegator,
            review.reviewer_ids,
            "Pending review should be reassigned back to the original user upon their return.",
        )
        self.assertNotIn(
            self.user_replacer_b,
            review.reviewer_ids,
            "Replacer should be removed from the review once the original user returns.",
        )
