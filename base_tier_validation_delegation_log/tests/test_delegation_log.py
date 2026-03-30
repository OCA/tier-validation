# Copyright 2025 360ERP (<https://www.360erp.com>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests.common import tagged

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation


@tagged("post_install", "-at_install")
class TestTierValidationDelegationLog(CommonTierValidation):
    def setUp(self):
        super().setUp()

        self.user_delegator = self.test_user_1

        # Give users the base internal user group to prevent portal/access quirks
        base_group_id = self.env.ref("base.group_user").id

        self.user_replacer_b = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "User B (Replacer)",
                    "login": "user_b",
                    "email": "b@test.com",
                    "groups_id": [Command.link(base_group_id)],
                }
            )
        )

        self.user_replacer_c = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "User C (Final)",
                    "login": "user_c",
                    "email": "c@test.com",
                    "groups_id": [Command.link(base_group_id)],
                }
            )
        )

        self.admin_user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Delegation Admin",
                    "login": "deleg_admin",
                    "email": "da@test.com",
                    "company_ids": [Command.link(self.env.company.id)],
                    "company_id": self.env.company.id,
                    "groups_id": [Command.link(base_group_id)],
                }
            )
        )

        self.delegation_admin_group = self.env.ref(
            "base_tier_validation_delegation.group_delegation_administrator",
            raise_if_not_found=False,
        )
        if self.delegation_admin_group:
            self.admin_user.write(
                {"groups_id": [Command.link(self.delegation_admin_group.id)]}
            )

        self.user_delegator.write(
            {"on_holiday": True, "validation_replacer_id": self.user_replacer_b.id}
        )

    def _create_record_and_request_validation(self, test_field_value=1):
        record = self.test_model.create({"test_field": test_field_value})

        record.with_user(self.test_user_2).request_validation()
        reviews = self.env["tier.review"].search([("res_id", "=", record.id)])

        return record, reviews

    def test_01_log_on_approval(self):
        record, reviews = self._create_record_and_request_validation()
        review = reviews[0]

        record.with_user(self.user_replacer_b).validate_tier()
        self.assertEqual(review.status, "approved")

        self.env.flush_all()
        log_entry = (
            self.env["tier.review.delegation.log"]
            .sudo()
            .search([("review_id", "=", review.id)])
        )

        if not log_entry:
            self.fail("Log entry was not created, blocking the multicompany test.")
            return

        self.assertEqual(len(log_entry), 1, "A delegation log entry was not created.")

    def test_02_log_on_rejection(self):
        record, reviews = self._create_record_and_request_validation()
        review = reviews[0]

        record.with_user(self.user_replacer_b).reject_tier()
        self.assertEqual(review.status, "rejected")

        self.env.flush_all()
        log_entry = (
            self.env["tier.review.delegation.log"]
            .sudo()
            .search([("review_id", "=", review.id)])
        )
        self.assertEqual(len(log_entry), 1, "A delegation log entry was not created.")

    def test_03_no_log_for_direct_review(self):
        self.user_delegator.write({"on_holiday": False})
        record, reviews = self._create_record_and_request_validation()
        review = reviews[0]

        record.with_user(self.user_delegator).validate_tier()

        self.env.flush_all()
        log_entry = (
            self.env["tier.review.delegation.log"]
            .sudo()
            .search([("review_id", "=", review.id)])
        )
        self.assertEqual(
            len(log_entry), 0, "Log should not be created for direct validation."
        )

        self.user_delegator.write({"on_holiday": True})

    def test_04_log_access_rights(self):
        record, reviews = self._create_record_and_request_validation()
        review = reviews[0]

        record.with_user(self.user_replacer_b).validate_tier()

        with self.assertRaises(
            AccessError, msg="Replacers should not be able to read delegation logs."
        ):
            self.env["tier.review.delegation.log"].with_user(
                self.user_replacer_b
            ).search([("review_id", "=", review.id)])

    def test_05_multicompany_isolation(self):
        company_2 = self.env["res.company"].create({"name": "Company 2"})
        record, reviews = self._create_record_and_request_validation()
        review = reviews[0]

        record.with_user(self.user_replacer_b).validate_tier()
        self.env.flush_all()

        log_entry = (
            self.env["tier.review.delegation.log"]
            .sudo()
            .search([("review_id", "=", review.id)])
        )

        if not log_entry:
            self.fail("Log entry was not created, blocking the multicompany test.")
        else:
            self.env.cr.execute(
                """
                UPDATE tier_review_delegation_log
                SET company_id = %s
                WHERE id = %s
                """,
                (company_2.id, log_entry.id),
            )

            visible_logs = (
                self.env["tier.review.delegation.log"]
                .with_user(self.admin_user)
                .with_context(allowed_company_ids=[self.env.company.id])
                .search([("review_id", "=", review.id)])
            )
            self.assertEqual(
                len(visible_logs), 0, "Log should be hidden across companies."
            )

    def test_06_global_log_visibility(self):
        record, reviews = self._create_record_and_request_validation()
        review = reviews[0]

        record.with_user(self.user_replacer_b).validate_tier()
        self.env.flush_all()

        log_entries = (
            self.env["tier.review.delegation.log"]
            .with_user(self.admin_user)
            .with_context(allowed_company_ids=[self.env.company.id])
            .search([("review_id", "=", review.id)])
        )
        self.assertEqual(len(log_entries), 1, "Admin A should see the global log.")

    def test_07_log_deletion_prevention(self):
        record, reviews = self._create_record_and_request_validation()
        review = reviews[0]

        record.with_user(self.user_replacer_b).validate_tier()
        self.env.flush_all()

        with self.assertRaises(
            AccessError,
            msg="Users should not be able to delete or read delegation logs.",
        ):
            log_entry = (
                self.env["tier.review.delegation.log"]
                .with_user(self.user_replacer_b)
                .search([("review_id", "=", review.id)])
            )
            log_entry.unlink()
