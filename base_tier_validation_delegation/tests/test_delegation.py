# Copyright 2026 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date, timedelta

from freezegun import freeze_time

from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation


@tagged("post_install", "-at_install")
class TestTierValidationDelegation(CommonTierValidation):
    def setUp(self):
        super().setUp()
        self.user_delegator = self.test_user_1
        self.user_replacer_b = self.env["res.users"].create(
            {"name": "User B (Replacer)", "login": "user_b", "email": "b@test.com"}
        )
        self.user_replacer_c = self.env["res.users"].create(
            {"name": "User C (Final)", "login": "user_c", "email": "c@test.com"}
        )
        self.admin_user = self.env["res.users"].create(
            {"name": "Delegation Admin", "login": "deleg_admin", "email": "da@test.com"}
        )
        self.delegation_admin_group = self.env.ref(
            "base_tier_validation_delegation.group_delegation_administrator"
        )
        self.admin_user.write(
            {"group_ids": [Command.link(self.delegation_admin_group.id)]}
        )

        self.test_group = self.env["res.groups"].create({"name": "Test Review Group"})
        self.test_user_1.write({"group_ids": [Command.link(self.test_group.id)]})
        self.test_user_2.write({"group_ids": [Command.link(self.test_group.id)]})

    def _create_record_and_request_validation(self, test_field_value=1):
        record = self.test_model.create({"test_field": test_field_value})
        record.with_user(self.test_user_2).request_validation()
        reviews = self.env["tier.review"].search([("res_id", "=", record.id)])
        self.assertTrue(reviews, "HELPER: Failed to create any tier reviews.")
        return record, reviews

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
        _record, review = self._create_record_and_request_validation()
        self.assertIn(self.user_delegator, review.reviewer_ids)
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
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
        (
            _record_while_away,
            review_while_away,
        ) = self._create_record_and_request_validation()
        self.assertIn(self.user_replacer_b, review_while_away.reviewer_ids)
        self.user_delegator.write({"on_holiday": False})
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
        (
            _record_after_return,
            review_after_return,
        ) = self._create_record_and_request_validation()
        self.assertIn(self.user_delegator, review_after_return.reviewer_ids)

    def test_07_no_replacer_configured(self):
        """Test that if 'On Holiday' is checked with no replacer,
        delegation does not occur."""
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
        """Test that delegation falls back to the original user
        if the replacer is archived."""
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

        self.assertEqual(tier1_review.status, "approved", "Tier 1 should be approved.")
        self.assertEqual(
            tier2_review.status, "pending", "Tier 2 should now be pending."
        )

    def test_17_delegation_by_field_reviewer(self):
        """
        Test Case for the Primary Fix.

        This test ensures that a pending review is correctly delegated when the
        reviewer was assigned via a dynamic field (`review_type` = 'field').
        This was the main cause of the cron job issue.
        """
        # Create a tier definition that uses a field to find the reviewer.
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

        # Create a record where the 'user_id' is our delegator
        record = self.test_model.create(
            {"test_field": 1.0, "user_id": self.user_delegator.id}
        )
        record.with_user(self.test_user_2).request_validation()
        review = self.env["tier.review"].search(
            [
                ("res_id", "=", record.id),
                ("definition_id", "=", field_tier_def.id),
            ]
        )

        self.assertTrue(review, "Test setup failed: Review was not created.")
        self.assertIn(
            self.user_delegator,
            review.reviewer_ids,
            "Initial reviewer should be the user from the 'user_id' field.",
        )

        # The user goes on holiday. This triggers the fixed `write`
        # method, which in turn calls the fixed `_recompute_reviews_for_users`.
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )

        # The pending review should now be assigned to the replacer.
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
        # User is on holiday, and a review is delegated to Replacer B.
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        _record, review = self._create_record_and_request_validation()

        self.assertIn(
            self.user_replacer_b,
            review.reviewer_ids,
            "Initial delegation to Replacer B should have occurred.",
        )
        self.assertNotIn(self.user_delegator, review.reviewer_ids)

        # While still on holiday, the user changes their replacer to C.
        # This triggers the improved `write` method in res.users.
        self.user_delegator.write({"validation_replacer_id": self.user_replacer_c.id})

        # The review should be moved from B to C.
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
        """
        # User is on holiday, and a review is delegated.
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        _record, review = self._create_record_and_request_validation()

        self.assertIn(
            self.user_replacer_b,
            review.reviewer_ids,
            "Review should be with the replacer while user is on holiday.",
        )

        # The user returns from holiday.
        self.user_delegator.write({"on_holiday": False})

        self.assertIn(
            self.user_delegator,
            review.reviewer_ids,
            "Pending review should be reassigned back to the original "
            "user upon their return.",
        )
        self.assertNotIn(
            self.user_replacer_b,
            review.reviewer_ids,
            "Replacer should be removed from the review "
            "once the original user returns.",
        )

    def test_20_field_reviewer_access_error_fix(self):
        """
        Test Case for the AccessError on ir.model.fields.
        """
        # Setup the ACL: base.group_user has 0,0,0,0 on ir.model.fields
        group_user = self.env.ref("base.group_user")

        # On existing rules for group_user on ir.model.fields: disable read access
        rules = (
            self.env["ir.model.access"]
            .sudo()
            .search(
                [
                    ("model_id.model", "=", "ir.model.fields"),
                    ("group_id", "=", group_user.id),
                ]
            )
        )
        rules.write(
            {
                "perm_read": False,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )

        # Ensure test_user_2 is ONLY in group_user (remove any admin rights)
        admin_groups = self.env.ref("base.group_erp_manager") | self.env.ref(
            "base.group_system"
        )
        self.test_user_2.write({"group_ids": [(3, g.id) for g in admin_groups]})

        # Setup Tier Definition
        reviewer_field = (
            self.env["ir.model.fields"]
            .sudo()
            .search(
                [("model", "=", "tier.validation.tester"), ("name", "=", "user_id")],
                limit=1,
            )
        )
        field_tier_def = (
            self.env["tier.definition"]
            .sudo()
            .create(
                {
                    "model_id": self.tester_model.id,
                    "review_type": "field",
                    "reviewer_field_id": reviewer_field.id,
                    "name": "Field-Based Review Strict ACL",
                }
            )
        )

        # Request validation
        record = self.test_model.sudo().create(
            {"test_field": 1.0, "user_id": self.test_user_2.id}
        )
        record.sudo().request_validation()

        review = (
            self.env["tier.review"]
            .sudo()
            .search(
                [("res_id", "=", record.id), ("definition_id", "=", field_tier_def.id)]
            )
        )
        self.assertTrue(review, "Review should be created successfully.")

        # This forces Odoo to query the database for reviewer_field_id.name,
        # triggering the ACL check.
        self.env.invalidate_all()

        # Call _get_reviewers() as test_user_2
        review.with_user(self.test_user_2)._get_reviewers()

    def test_21_delegation_admin_is_not_settings_admin(self):
        """The delegation administrator only manages delegation settings."""
        self.assertFalse(self.admin_user.has_group("base.group_system"))
        self.assertTrue(
            self.env.ref("base.user_admin").has_group(
                "base_tier_validation_delegation.group_delegation_administrator"
            )
        )
        with self.assertRaises(AccessError):
            self.user_delegator.with_user(self.admin_user).write(
                {"on_holiday": True, "name": "Renamed"}
            )

    def _create_stale_delegation(self):
        """A review still assigned to the delegator whose holiday started today.

        The holiday starts tomorrow, so the review is created for the
        delegator; the tests then act as if it were tomorrow, before anything
        recomputed the reviewers.
        """
        tomorrow = date.today() + timedelta(days=1)
        self.user_delegator.write(
            {
                "on_holiday": True,
                "holiday_start_date": tomorrow,
                "validation_replacer_id": self.user_replacer_b.id,
            }
        )
        record, review = self._create_record_and_request_validation()
        self.assertEqual(review.reviewer_ids, self.user_delegator)
        return record, review, tomorrow

    def test_22_validate_as_delegate(self):
        """A replacer can validate a review not yet reassigned to them."""
        record, review, tomorrow = self._create_stale_delegation()
        with freeze_time(tomorrow):
            record.with_user(self.user_replacer_b).validate_tier()
        self.assertEqual(review.status, "approved")
        self.assertEqual(review.done_by, self.user_replacer_b)

    def test_23_reject_as_delegate(self):
        """A replacer can reject a review not yet reassigned to them."""
        record, review, tomorrow = self._create_stale_delegation()
        with freeze_time(tomorrow):
            _res, delegator, rejected = record.with_user(
                self.user_replacer_b
            )._rejected_tier()
        self.assertEqual(review.status, "rejected")
        self.assertEqual(review.done_by, self.user_replacer_b)
        self.assertEqual(delegator, self.user_delegator)
        self.assertEqual(rejected, review)

    def test_24_reject_as_assigned_replacer(self):
        """Rejecting a delegated review reports who delegated it."""
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        record, review = self._create_record_and_request_validation()
        self.assertEqual(review.reviewer_ids, self.user_replacer_b)
        _res, delegator, rejected = record.with_user(
            self.user_replacer_b
        )._rejected_tier()
        self.assertEqual(review.status, "rejected")
        self.assertEqual(delegator, self.user_delegator)
        self.assertEqual(rejected, review)

    def test_25_validate_without_delegation(self):
        """A user who is neither reviewer nor replacer cannot validate."""
        record, review = self._create_record_and_request_validation()
        record.with_user(self.user_replacer_c)._validate_tier()
        self.assertEqual(review.status, "pending")

    def test_26_holiday_end_before_start(self):
        with self.assertRaises(ValidationError):
            self.user_delegator.write(
                {
                    "on_holiday": True,
                    "holiday_start_date": date.today(),
                    "holiday_end_date": date.today() - timedelta(days=1),
                }
            )

    def test_27_is_currently_on_holiday_defaults_to_today(self):
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        self.assertTrue(self.user_delegator._is_currently_on_holiday())

    def test_28_circular_delegation_at_runtime(self):
        """A loop the constraint did not see falls back to the last user."""
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        # Only possible by bypassing the constraint, e.g. with SQL.
        self.env.cr.execute(
            "UPDATE res_users SET on_holiday = true, validation_replacer_id = %s "
            "WHERE id = %s",
            (self.user_delegator.id, self.user_replacer_b.id),
        )
        self.env.invalidate_all()
        with mute_logger(
            "odoo.addons.base_tier_validation_delegation.models.res_users"
        ):
            replacer = self.user_delegator._get_final_validation_replacer()
        self.assertEqual(replacer, self.user_replacer_b)

    def test_29_cron_holiday_reminder(self):
        """Users starting a holiday in 3 days without replacer are reminded."""
        users = self.env["res.users"]
        # Nothing to activate or deactivate today.
        users._cron_update_holiday_status()
        self.user_replacer_c.holiday_start_date = date.today() + timedelta(days=3)
        partner = self.user_replacer_c.partner_id
        messages_before = partner.message_ids
        users._cron_send_delegation_reminder()
        new_messages = partner.message_ids - messages_before
        self.assertIn(
            "configure a validation replacer",
            " ".join(str(m.body) for m in new_messages),
        )

    def test_30_nothing_to_recompute(self):
        self.assertTrue(self.env["res.users"].write({"on_holiday": False}))
        self.assertIsNone(
            self.env["tier.review"]._recompute_reviews_for_users(self.env["res.users"])
        )

    def test_31_delegate_review_without_document(self):
        """A review without document is delegated, without chatter message."""
        review = self.env["tier.review"].create(
            {
                "definition_id": self.definition_1.id,
                "model": self.test_model._name,
                "status": "pending",
            }
        )
        self.assertEqual(review.reviewer_ids, self.user_delegator)
        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )
        self.assertEqual(review.reviewer_ids, self.user_replacer_b)
        self.assertEqual(review.delegated_by_ids, self.user_delegator)

    def test_32_inside_delegation_flow(self):
        """Within the delegation flow, the base behaviour applies as is."""
        record, review = self._create_record_and_request_validation()
        record.with_user(self.user_delegator).with_context(
            in_delegation_flow=True
        )._validate_tier()
        self.assertEqual(review.status, "approved")
        record, review = self._create_record_and_request_validation()
        _res, delegator, rejected = (
            record.with_user(self.user_delegator)
            .with_context(in_delegation_flow=True)
            ._rejected_tier()
        )
        self.assertEqual(review.status, "rejected")
        self.assertFalse(delegator)
        self.assertFalse(rejected)

    def test_33_reject_without_delegation(self):
        """A user who is neither reviewer nor replacer cannot reject."""
        record, review = self._create_record_and_request_validation()
        _res, delegator, rejected = record.with_user(
            self.user_replacer_c
        )._rejected_tier()
        self.assertEqual(review.status, "pending")
        self.assertFalse(delegator)
        self.assertFalse(rejected)
