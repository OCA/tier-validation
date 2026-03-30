# Copyright 2025 360ERP (<https://www.360erp.com>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class TierReviewDelegationLog(models.Model):
    _name = "tier.review.delegation.log"
    _description = "Tier Review Delegation Log"
    _order = "action_date desc"

    review_id = fields.Many2one("tier.review", string="Review", ondelete="set null")
    record_ref = fields.Reference(
        string="Document",
        selection="_selection_record_ref",
        readonly=True,
    )
    delegator_id = fields.Many2one("res.users", string="Delegator", readonly=True)
    replacer_id = fields.Many2one("res.users", string="Replacer", readonly=True)
    action = fields.Selection(
        [("approved", "Approved"), ("rejected", "Rejected")],
        readonly=True,
    )
    action_date = fields.Datetime(default=fields.Datetime.now)
    company_id = fields.Many2one(
        "res.company", compute="_compute_company_id", store=True, index=True
    )

    @api.depends("review_id")
    def _compute_company_id(self):
        for rec in self:
            if (
                rec.review_id
                and rec.review_id.model
                and rec.review_id.model in self.env
                and rec.review_id.res_id
            ):
                model = self.env[rec.review_id.model]
                record = model.browse(rec.review_id.res_id)

                # Safely check for company_id
                if "company_id" in record and record.company_id:
                    rec.company_id = record.company_id.id
                else:
                    rec.company_id = False
            else:
                # Fallback to False
                rec.company_id = False

    def _selection_record_ref(self):
        """
        Find all models that have at least one tier definition,
        as this is the correct way to identify models using tier validation.
        """
        # Search on tier.definition instead of the non-stored is_tier_validation field
        tier_definition_models = (
            self.env["tier.definition"].search([]).mapped("model_id")
        )
        return [(m.model, m.name) for m in tier_definition_models]
