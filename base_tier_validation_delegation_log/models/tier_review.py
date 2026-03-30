# Copyright 2026 360ERP (<https://www.360erp.com>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models


class TierReview(models.Model):
    _inherit = "tier.review"

    def write(self, vals):
        target_status = vals.get("status")
        if target_status not in ("approved", "rejected"):
            return super().write(vals)

        records_to_check = self.filtered(lambda r: r.status != target_status)

        res = super().write(vals)

        if not records_to_check:
            return res

        logs_to_create = []
        current_user = self.env.user

        for rec in records_to_check:
            if rec.status == target_status:
                delegators = rec.delegated_by_ids
                if not delegators:
                    original = rec._get_original_reviewers()
                    delegators = original - rec.reviewer_ids

                for delegator in delegators:
                    if delegator != current_user:
                        logs_to_create.append(
                            {
                                "review_id": rec.id,
                                "record_ref": f"{rec.model},{rec.res_id}",
                                "delegator_id": delegator.id,
                                "replacer_id": current_user.id,
                                "action": rec.status,
                            }
                        )

        if logs_to_create:
            self.env["tier.review.delegation.log"].sudo().create(logs_to_create)

        return res
