# Copyright 2026 360ERP (https://www.360erp.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountMoveTierValidationApproverGroup(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.approver_group = cls.env["res.groups"].create(
            {"name": "Vendor Bill Approvers"}
        )
        cls.group_approver = new_test_user(
            cls.env,
            name="Group Approver",
            login="group_approver",
            groups="base.group_user,account.group_account_manager",
        )
        cls.group_approver.group_ids += cls.approver_group
        cls.other_user = new_test_user(
            cls.env,
            name="Other User",
            login="other_user",
            groups="base.group_user,account.group_account_manager",
        )
        cls.single_approver = new_test_user(
            cls.env,
            name="Single Approver",
            login="single_approver",
            groups="base.group_user,account.group_account_manager",
        )
        cls.vendor = cls.env["res.partner"].create(
            {
                "name": "Vendor with approver group",
                "approver_group_id": cls.approver_group.id,
            }
        )
        cls.vendor_no_group = cls.env["res.partner"].create(
            {"name": "Vendor without approver group"}
        )
        cls.product = cls.env["product.product"].create({"name": "Desk"})
        # Only keep the tiers created by these tests
        cls.env["tier.definition"].search([]).action_archive()

    def _create_bill(self, partner, **values):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "invoice_date": "2025-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "quantity": 1,
                            "price_unit": 100,
                        }
                    )
                ],
                **values,
            }
        )

    def _settings(self, **values):
        config = self.env["res.config.settings"].create(values)
        config.set_values()
        return config

    def test_01_compute_approver_group_id(self):
        """The group comes from the vendor and can be changed by hand."""
        move = self.env["account.move"].new(
            {"move_type": "in_invoice", "partner_id": self.vendor_no_group.id}
        )
        self.assertFalse(move.approver_group_id)
        move.partner_id = self.vendor
        self.assertEqual(move.approver_group_id, self.approver_group)
        other_group = self.env["res.groups"].create({"name": "Other approvers"})
        move.approver_group_id = other_group
        move._compute_approver_group_id()
        self.assertEqual(move.approver_group_id, other_group)

    def test_02_compute_keeps_individual_approver(self):
        """Computing the group never removes the individual approver."""
        bill = self._create_bill(
            self.vendor_no_group, approver_id=self.single_approver.id
        )
        self.assertFalse(bill.approver_group_id)
        self.assertEqual(bill.approver_id, self.single_approver)
        bill._compute_approver_group_id()
        self.assertEqual(bill.approver_id, self.single_approver)

    def test_03_settings_are_independent(self):
        """The group option does not change the individual option."""
        self._settings(
            require_approver_in_vendor_bills=False,
            require_approver_group_in_vendor_bills=True,
        )
        company = self.env.company
        self.assertTrue(company.require_approver_group_in_vendor_bills)
        self.assertFalse(company.require_approver_in_vendor_bills)
        tier = company.validation_approver_group_tier_definition_id
        self.assertTrue(tier.active)
        self.assertEqual(tier.reviewer_field_id.name, "approver_group_id")
        self.assertIn("approver_group_id", tier.definition_domain)
        self._settings(require_approver_group_in_vendor_bills=False)
        self.assertFalse(tier.active)
        self.assertFalse(company.require_approver_group_in_vendor_bills)

    def test_04_post_requires_user_or_group(self):
        self._settings(require_approver_group_in_vendor_bills=True)
        bill = self._create_bill(self.vendor_no_group)
        with self.assertRaisesRegex(UserError, "user or group"):
            bill._post()
        # A group is enough
        bill.approver_group_id = self.approver_group
        bill._check_has_approver()
        # A user is enough too
        bill.approver_group_id = False
        bill.approver_id = self.single_approver
        bill._check_has_approver()

    def test_05_individual_setting_accepts_group(self):
        """With the individual option, a bill with only a group can be posted."""
        self._settings(require_approver_in_vendor_bills=True)
        bill = self._create_bill(self.vendor)
        self.assertFalse(bill.approver_id)
        self.assertEqual(bill.approver_group_id, self.approver_group)
        bill._check_has_approver()

    def test_06_group_member_validates(self):
        self._settings(require_approver_group_in_vendor_bills=True)
        bill = self._create_bill(self.vendor)
        bill.with_user(self.other_user).request_validation()
        bill.invalidate_recordset()
        self.assertIn(self.group_approver, bill.reviewer_ids)
        self.assertNotIn(self.other_user, bill.reviewer_ids)
        bill.with_user(self.other_user).validate_tier()
        with self.assertRaises(ValidationError):
            bill.action_post()
        bill.with_user(self.group_approver).validate_tier()
        bill.action_post()
        self.assertEqual(bill.state, "posted")

    def test_07_group_tier_skipped_without_group(self):
        """The default group tier does not apply to bills without a group."""
        self._settings(require_approver_group_in_vendor_bills=True)
        bill = self._create_bill(
            self.vendor_no_group, approver_id=self.single_approver.id
        )
        self.assertFalse(bill.need_validation)
