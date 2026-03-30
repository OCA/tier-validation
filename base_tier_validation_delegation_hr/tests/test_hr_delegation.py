# Copyright 2025 360ERP (<https://www.360erp.com>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from datetime import date, timedelta

from odoo.fields import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrDelegation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_delegator = cls.env["res.users"].create(
            {
                "name": "Delegator User",
                "login": "delegator_user",
                "email": "delegator@test.com",
            }
        )

        cls.user_replacer = cls.env["res.users"].create(
            {
                "name": "Replacer User",
                "login": "replacer_user",
                "email": "replacer@test.com",
            }
        )

        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Delegator Employee",
                "user_id": cls.user_delegator.id,
            }
        )

    def test_01_sync_employee_to_user_boolean(self):
        """Test that setting 'On Holiday' on Employee updates User."""
        self.assertFalse(
            self.user_delegator.on_holiday, "User should start not on holiday"
        )

        self.employee.write({"tier_on_holiday": True})
        self.assertTrue(
            self.user_delegator.on_holiday,
            "User should be marked on holiday after Employee update",
        )

        self.employee.write({"tier_on_holiday": False})
        self.assertFalse(
            self.user_delegator.on_holiday,
            "User should be unmarked after Employee update",
        )

    def test_02_sync_employee_to_user_replacer(self):
        """Test that setting 'Replacer' on Employee updates User."""
        self.assertFalse(
            self.user_delegator.validation_replacer_id,
            "User should start with no replacer",
        )

        self.employee.write({"tier_validation_replacer_id": self.user_replacer.id})
        self.assertEqual(
            self.user_delegator.validation_replacer_id,
            self.user_replacer,
            "User's replacer should match the one set on Employee",
        )

    def test_03_sync_employee_to_user_dates(self):
        """Test that setting dates on Employee updates User."""
        start_date = date.today()
        end_date = date.today() + timedelta(days=5)

        self.employee.write(
            {
                "tier_holiday_start_date": start_date,
                "tier_holiday_end_date": end_date,
            }
        )
        self.assertEqual(self.user_delegator.holiday_start_date, start_date)
        self.assertEqual(self.user_delegator.holiday_end_date, end_date)

    def test_04_read_consistency(self):
        """Test that reading from Employee reflects changes made directly on User."""
        self.user_delegator.write({"on_holiday": True})

        self.assertTrue(
            self.employee.tier_on_holiday,
            "Employee field should reflect changes made to User",
        )

    def test_05_employee_without_user(self):
        """Test creating an employee without a user (ensure no crash on view/read)."""
        employee_no_user = self.env["hr.employee"].create(
            {
                "name": "Employee No User",
                # user_id is False
            }
        )

        self.assertFalse(employee_no_user.tier_on_holiday)
        self.assertFalse(employee_no_user.tier_validation_replacer_id)

    def test_06_res_users_profile(self):
        # As a user without HR Officer rights I can read my own profile
        user = self.env["res.users"].create(
            {
                "login": "test@example.org",
                "name": "Test",
                "groups_id": [Command.set(self.env.ref("base.group_user").ids)],
            },
        )
        user.with_user(user).with_context(
            **{
                "lang": "en_US",
                "tz": "Europe/Amsterdam",
                "uid": user.id,
                "allowed_company_ids": [self.env.company.id],
                "bin_size": True,
                "from_my_profile": True,
            }
        ).web_read(
            specification={
                "on_holiday": {},
                "holiday_start_date": {},
                "holiday_end_date": {},
                "validation_replacer_id": {
                    "fields": {"display_name": {}},
                    "context": {"active_test": False},
                },
                # Need one group protected field to trigger the error
                "private_street": {},
            }
        )
