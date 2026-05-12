# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Digest(models.Model):
    _inherit = "digest.digest"

    # Per-user: reviews you can act on right now.
    kpi_tier_validation_pending = fields.Boolean(
        string="Tier reviews pending for you",
    )
    kpi_tier_validation_pending_value = fields.Integer(
        compute="_compute_kpi_tier_validation_pending_value",
    )
    # Per-user: reviews queued behind a lower-sequence tier the user is not
    # yet allowed to act on. Useful when ``approve_sequence`` is in play so
    # the recipient can see what is coming.
    kpi_tier_validation_waiting = fields.Boolean(
        string="Tier reviews queued for you",
    )
    kpi_tier_validation_waiting_value = fields.Integer(
        compute="_compute_kpi_tier_validation_waiting_value",
    )
    # Per-user, period-scoped: a "you cleared X this week" signal.
    kpi_tier_validation_validated_period = fields.Boolean(
        string="Tier reviews you validated this period",
    )
    kpi_tier_validation_validated_period_value = fields.Integer(
        compute="_compute_kpi_tier_validation_validated_period_value",
    )
    # Manager view: total pending across the company. Gated to managers via
    # the ``groups`` attribute on the boolean toggle -- ordinary users will
    # not see the configuration field, so they cannot enable the tile on
    # their own digest preferences.
    kpi_tier_validation_pending_team = fields.Boolean(
        string="Tier reviews pending across team",
        groups="base.group_erp_manager",
    )
    kpi_tier_validation_pending_team_value = fields.Integer(
        compute="_compute_kpi_tier_validation_pending_team_value",
        groups="base.group_erp_manager",
    )

    # The four computes intentionally do NOT declare ``@api.depends``: KPI
    # values are point-in-time snapshots called at digest-send time by the
    # ``available_fields`` machinery and never need ORM cache invalidation.

    def _compute_kpi_tier_validation_pending_value(self):
        for record in self:
            user = self.env.user
            record.kpi_tier_validation_pending_value = self.env[
                "tier.review"
            ].search_count(
                [
                    ("status", "=", "pending"),
                    ("reviewer_ids", "in", user.id),
                    ("can_review", "=", True),
                ]
            )

    def _compute_kpi_tier_validation_waiting_value(self):
        for record in self:
            user = self.env.user
            record.kpi_tier_validation_waiting_value = self.env[
                "tier.review"
            ].search_count(
                [
                    ("status", "=", "waiting"),
                    ("reviewer_ids", "in", user.id),
                ]
            )

    def _compute_kpi_tier_validation_validated_period_value(self):
        for record in self:
            start, end, _companies = record._get_kpi_compute_parameters()
            user = self.env.user
            record.kpi_tier_validation_validated_period_value = self.env[
                "tier.review"
            ].search_count(
                [
                    ("status", "=", "approved"),
                    ("done_by", "=", user.id),
                    ("reviewed_date", ">=", start),
                    ("reviewed_date", "<", end),
                ]
            )

    def _compute_kpi_tier_validation_pending_team_value(self):
        # ``groups`` on the field already restricts read access to managers;
        # non-managers reading this field raise AccessError before the
        # compute runs. The digest's send loop catches that and skips the
        # KPI for that user.
        for record in self:
            _start, _end, companies = record._get_kpi_compute_parameters()
            record.kpi_tier_validation_pending_team_value = self.env[
                "tier.review"
            ].search_count(
                [
                    ("status", "=", "pending"),
                    ("company_id", "in", companies.ids),
                ]
            )

    def _compute_kpis_actions(self, company, user):
        """Wire each KPI tile to the corresponding ``tier.review`` action.

        ``digest._compute_kpis_actions`` returns a dict ``{kpi_field: token}``
        where the token is concatenated into ``/odoo/action-<token>`` to form
        the click-through URL.
        """
        res = super()._compute_kpis_actions(company, user)
        menu_id = self.env.ref(
            "base_tier_validation.menu_tier_confirmation",
            raise_if_not_found=False,
        )
        menu_part = f"&menu_id={menu_id.id}" if menu_id else ""
        my_action = self.env.ref(
            "tier_validation_digest.action_my_tier_reviews",
            raise_if_not_found=False,
        )
        team_action = self.env.ref(
            "tier_validation_digest.action_team_pending_tier_reviews",
            raise_if_not_found=False,
        )
        if my_action:
            for kpi in (
                "kpi_tier_validation_pending",
                "kpi_tier_validation_waiting",
                "kpi_tier_validation_validated_period",
            ):
                res[kpi] = f"{my_action.id}{menu_part}"
        if team_action:
            res["kpi_tier_validation_pending_team"] = f"{team_action.id}{menu_part}"
        return res
