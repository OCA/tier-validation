# Copyright 2019 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models, modules
from odoo.exceptions import AccessError
from odoo.fields import Domain

_logger = logging.getLogger(__name__)

# Default for the ``base_tier_validation.late_after_days`` system parameter
# used by the systray to split pending reviews into a "Late" bucket.
DEFAULT_LATE_AFTER_DAYS = 7


class Users(models.Model):
    _inherit = "res.users"

    review_ids = fields.Many2many(
        string="Reviews", comodel_name="tier.review", copy=False
    )

    @api.model
    def review_user_count(self):
        """Counts driving the tier-review systray dropdown.

        Each returned dict represents one model that has reviews touching
        the current user and reports three buckets so the dropdown can
        mirror Odoo's activity systray layout:

        - ``late_count`` -- pending reviews older than the configured
          *late* threshold (``base_tier_validation.late_after_days``,
          default ``7``). The reviewer should prioritise these.
        - ``pending_count`` -- pending reviews within the threshold.
          Standard work the reviewer can act on today.
        - ``future_count`` -- waiting reviews where the current user is
          assigned as reviewer but the sequence has not yet promoted the
          review to pending. "What is incoming for me".

        The per-bucket record ids are returned alongside the counts so
        clicking a bucket in the systray opens exactly those records.
        """
        user_reviews = {}
        user = self.env.user
        user.review_ids._update_review_status()
        late_after_days = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "base_tier_validation.late_after_days",
                default=str(DEFAULT_LATE_AFTER_DAYS),
            )
        )
        late_cutoff = fields.Datetime.subtract(
            fields.Datetime.now(), days=late_after_days
        )
        # Fetch every actionable review touching this user (pending +
        # waiting) in one read_group so we only pay the SQL cost once.
        domain = Domain("status", "in", ["pending", "waiting"]) & Domain(
            "id", "in", user.review_ids.ids
        )
        review_groups = self.env["tier.review"]._read_group(
            domain=domain,
            groupby=["model"],
            aggregates=["id:recordset"],
        )
        for model, tier_reviews in review_groups:
            Model = self.env.get(model)
            if Model is None or not hasattr(Model, "can_review"):
                # Tier-validation has been uninstalled for this model
                # since the reviews were created. Skip silently.
                continue
            pending_reviews = tier_reviews.filtered(
                lambda r: r.status == "pending" and r.can_review
            )
            future_reviews = tier_reviews.filtered(lambda r: r.status == "waiting")
            late_reviews = pending_reviews.filtered(
                lambda r: r.create_date and r.create_date < late_cutoff
            )
            try:
                # Resolve pending reviews to their underlying records,
                # honouring ACL + record rules + the active flag.
                pending_records = (
                    Model.with_user(user)
                    .with_context(active_test=False)
                    .search(
                        Domain("id", "in", pending_reviews.mapped("res_id"))
                        & Domain("validation_status", "!=", "rejected")
                        & Domain("can_review", "=", True)
                    )
                )
                future_records = (
                    Model.with_user(user)
                    .with_context(active_test=False)
                    .search(
                        Domain("id", "in", future_reviews.mapped("res_id"))
                        & Domain("validation_status", "!=", "rejected")
                    )
                )
            except AccessError:
                # Reviewer was assigned to a model they have no read
                # access to. Drop it from the systray; the workflow is
                # stuck for a config reason and #30 / #32 surface that
                # elsewhere.
                _logger.debug(
                    "User %s has no read access to %s; skipping in systray.",
                    user.login,
                    model,
                )
                continue
            # Filter out cancelled records the same way the model does
            # when it has a state/cancel convention.
            if Model._state_field in Model._fields:
                pending_records = pending_records.filtered(
                    lambda x: x[x._state_field] != x._cancel_state
                )
                future_records = future_records.filtered(
                    lambda x: x[x._state_field] != x._cancel_state
                )
            late_res_ids = set(late_reviews.mapped("res_id"))
            late_records = pending_records.filtered(
                lambda x, late_res_ids=late_res_ids: x.id in late_res_ids
            )
            pending_ontime_records = pending_records - late_records
            if not (late_records or pending_ontime_records or future_records):
                continue
            first_record = (
                late_records[:1] or pending_ontime_records[:1] or future_records[:1]
            )
            user_reviews[model] = {
                "id": first_record.id,
                "name": Model._description,
                "model": model,
                "active_field": "active" in Model._fields,
                "icon": modules.module.get_module_icon(Model._original_module),
                "type": "tier_review",
                "late_count": len(late_records),
                "pending_count": len(pending_ontime_records),
                "future_count": len(future_records),
                "late_ids": late_records.ids,
                "pending_ids": pending_ontime_records.ids,
                "future_ids": future_records.ids,
            }
        return list(user_reviews.values())
