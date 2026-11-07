# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class CommentWizard(models.TransientModel):
    _inherit = "comment.wizard"

    def add_comment(self):
        """Without ``res_id``, the comment was asked for several documents
        selected in a list: review them all with it."""
        if self.res_id:
            return super().add_comment()
        self.ensure_one()
        records = self.env[self.res_model].browse(set(self.review_ids.mapped("res_id")))
        return records._multi_review_tier(self.validate_reject, comment=self.comment)
