# Copyright 2025 360 ERP
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    approver_group_id = fields.Many2one(
        "res.groups",
        string="Group responsible for approval",
        compute="_compute_approver_group_id",
        readonly=False,
        store=True,
    )

    @api.depends("partner_id")
    def _compute_approver_group_id(self):
        for rec in self:
            if rec.approver_group_id:
                # assign a value in any case
                rec.approver_group_id = rec.approver_group_id
            elif rec.partner_id.approver_group_id:
                rec.approver_group_id = rec.partner_id.approver_group_id
            else:
                rec.approver_group_id = False

    def _check_has_approver(self):
        """Take the approver group into account.

        When an approver (user) or an approver group is required, a vendor
        bill can be posted if it has a user OR a group responsible for
        the approval.
        """
        self.ensure_one()
        company = self.company_id
        approver_required = (
            company.require_approver_in_vendor_bills
            or company.require_approver_group_in_vendor_bills
        )
        if (
            self.is_purchase_document(include_receipts=True)
            and approver_required
            and not self.approver_id
            and not self.approver_group_id
        ):
            raise UserError(
                self.env._(
                    "It is mandatory to indicate a Responsible for Approval "
                    "(user or group) (in %s)",
                    self.name,
                )
            )
