# Copyright 2025 360ERP (<https://www.360erp.com>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    tier_on_holiday = fields.Boolean(
        string="On Holiday (Tier Validation)",
        related="user_id.on_holiday",
        readonly=False,
        store=True,
        help="If checked, tier validations will be delegated to the replacer.",
    )

    tier_holiday_start_date = fields.Date(
        string="Holiday Start Date",
        compute="_compute_tier_holiday_dates",
        inverse="_inverse_tier_holiday_dates",
        store=True,
    )

    tier_holiday_end_date = fields.Date(
        string="Holiday End Date",
        compute="_compute_tier_holiday_dates",
        inverse="_inverse_tier_holiday_dates",
        store=True,
    )

    tier_validation_replacer_id = fields.Many2one(
        comodel_name="res.users",
        string="Tier Validation Replacer",
        related="user_id.validation_replacer_id",
        readonly=False,
        store=True,
        help="The user who will receive validation requests while "
        "this employee is on holiday.",
    )

    @api.depends("user_id.holiday_start_date", "user_id.holiday_end_date")
    def _compute_tier_holiday_dates(self):
        for employee in self:
            if employee.user_id:
                employee.tier_holiday_start_date = employee.user_id.holiday_start_date
                employee.tier_holiday_end_date = employee.user_id.holiday_end_date
            else:
                employee.tier_holiday_start_date = False
                employee.tier_holiday_end_date = False

    def _inverse_tier_holiday_dates(self):
        for employee in self:
            if employee.user_id:
                employee.user_id.write(
                    {
                        "holiday_start_date": employee.tier_holiday_start_date,
                        "holiday_end_date": employee.tier_holiday_end_date,
                    }
                )
