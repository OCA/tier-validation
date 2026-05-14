# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CommentWizard(models.TransientModel):
    _name = "comment.wizard"
    _description = "Comment Wizard"

    validate_reject = fields.Char()
    res_model = fields.Char()
    res_id = fields.Integer()
    review_ids = fields.Many2many(comodel_name="tier.review")
    comment = fields.Char(required=True)
    bulk_skipped = fields.Integer(
        help="Reviews of a bulk selection that cannot be processed in bulk."
    )

    def add_comment(self):
        self.ensure_one()
        if self.validate_reject == "bulk_reject":
            reviews = self.review_ids._filter_bulk_reviewable()
            reviews._bulk_process("reject", self.comment)
            skipped = self.bulk_skipped + len(self.review_ids - reviews)
            return reviews._bulk_result("reject", skipped)
        rec = self.env[self.res_model].browse(self.res_id)
        self.review_ids.write({"comment": self.comment})
        if self.validate_reject == "validate":
            rec._validate_tier(self.review_ids)
        if self.validate_reject == "reject":
            rec._rejected_tier(self.review_ids)
        rec._update_counter({"review_deleted": True})
