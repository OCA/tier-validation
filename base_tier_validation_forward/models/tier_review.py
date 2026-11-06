# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class TierReview(models.Model):
    _inherit = "tier.review"

    # NOTE: Added translate=True because in the compute method we assign:
    #   rec.name = rec.definition_id.name
    # And the field `name` in `tier.definition` is translated (translate=True),
    # so we must match this behavior.
    # Reference: https://github.com/OCA/server-ux/pull/1065#discussion_r2058502638
    name = fields.Char(
        compute="_compute_definition_data", store=True, related=False, translate=True
    )
    status = fields.Selection(
        selection_add=[("forwarded", "Forwarded")],
    )
    # Stored so forwarded reviews (no definition) keep the wizard values.
    review_type = fields.Selection(
        store=True,
    )
    reviewer_id = fields.Many2one(
        comodel_name="res.users",
        store=True,
    )
    reviewer_group_id = fields.Many2one(
        comodel_name="res.groups",
        store=True,
    )
    sequence = fields.Integer()
    has_comment = fields.Boolean(
        store=True,
    )
    approve_sequence = fields.Boolean(
        store=True,
    )

    @api.depends("definition_id.name")
    def _compute_definition_data(self):
        for rec in self:
            rec.name = rec.definition_id.name
