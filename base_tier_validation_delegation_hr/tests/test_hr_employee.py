# Copyright 2026 360ERP (<https://www.360erp.com>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from datetime import date

from odoo.tests.common import TransactionCase


class TestHrEmployeeTierHoliday(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # 1. Create a user with an initial valid holiday range
        cls.user = cls.env["res.users"].create(
            {
                "name": "Holiday User",
                "login": "holiday_user",
                "on_holiday": True,
                "holiday_start_date": date(2025, 5, 10),
                "holiday_end_date": date(2025, 5, 20),
            }
        )

        # 2. Create an employee linked to that user
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Holiday Employee",
                "user_id": cls.user.id,
            }
        )

    def test_simultaneous_date_update_no_validation_error(self):
        """
        Test that updating both start and end dates simultaneously on the employee
        does not trigger the 'End Date cannot be before Start Date' constraint.
        This proves the inverse method correctly groups the write operation.
        """
        # We attempt to shift the entire holiday range forward.
        # If evaluated sequentially (e.g., Start Date updated first),
        # the new Start Date (June 10) would be greater than the old End Date (May 20),
        # triggering a ValidationError.

        # With our inverse method, this single write should succeed.
        self.employee.write(
            {
                "tier_holiday_start_date": date(2025, 6, 10),
                "tier_holiday_end_date": date(2025, 6, 20),
            }
        )

        # Verify the dates were actually updated correctly on the underlying user
        self.assertEqual(self.user.holiday_start_date, date(2025, 6, 10))
        self.assertEqual(self.user.holiday_end_date, date(2025, 6, 20))
