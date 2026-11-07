# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from lxml import etree

from odoo import api, models
from odoo.exceptions import UserError


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type in ("list", "kanban") and self._tier_validation_multi_enabled():
            doc = etree.fromstring(res["arch"])
            self._add_tier_validation_multi_buttons(doc)
            res["arch"] = etree.tostring(doc, encoding="unicode")
        return res

    @api.model
    def _tier_validation_multi_enabled(self):
        """Whether an active definition of this model allows multi validation,
        in any company: the view must not depend on the user's company."""
        definitions = self.env["tier.definition"].sudo().with_context(active_test=True)
        return bool(
            definitions.search_count(
                [("model", "=", self._name), ("allow_multi_validate", "=", True)],
                limit=1,
            )
        )

    @api.model
    def _get_tier_validation_multi_buttons(self):
        """Return the header buttons, shown on the selected records."""
        return [
            etree.Element(
                "button",
                name="action_multi_request_validation",
                type="object",
                string=self.env._("Request Validation"),
            ),
            etree.Element(
                "button",
                name="action_multi_validate_tier",
                type="object",
                string=self.env._("Validate"),
                icon="thumb_up",
                icon_class="oi-filled",
            ),
            etree.Element(
                "button",
                name="action_multi_reject_tier",
                type="object",
                string=self.env._("Reject"),
                icon="thumb_down",
                icon_class="oi-filled",
                confirm=self.env._("Reject the selected documents?"),
            ),
        ]

    @api.model
    def _add_tier_validation_multi_buttons(self, doc):
        """Append the buttons to the last header of the view (the only one a
        list view reads), created when missing."""
        headers = doc.findall("header")
        if headers:
            header = headers[-1]
        else:
            header = etree.Element("header")
            doc.insert(0, header)
        present = {button.get("name") for button in header.iter("button")}
        for button in self._get_tier_validation_multi_buttons():
            if button.get("name") not in present:
                header.append(button)

    def action_multi_request_validation(self):
        records = self.filtered("need_validation")
        if not records:
            raise UserError(
                self.env._("None of the selected documents needs a validation request.")
            )
        records.request_validation()
        return self._notify_tier_validation_multi(
            self.env._("Validation requested for %s document(s).", len(records)),
            len(self) - len(records),
        )

    def action_multi_validate_tier(self):
        return self._multi_review_tier("validate")

    def action_multi_reject_tier(self):
        return self._multi_review_tier("reject")

    def _multi_review_tier(self, validate_reject, comment=False):
        """Validate or reject the selected documents that the current user can
        review from the list.

        A review asking for a comment takes the given ``comment``; else, when
        validating, the default approve comment of its definition. When one is
        still missing, ask for it once for all documents.
        """
        self.check_access("read")
        to_process = []
        for rec in self:
            rec_reviews = rec._get_multi_tier_reviews(validate_reject)
            if rec_reviews:
                to_process.append((rec, rec_reviews))
        if not to_process:
            raise UserError(
                self.env._("None of the selected documents can be reviewed by you.")
            )
        reviews = self.env["tier.review"].browse(
            [review.id for _rec, rec_reviews in to_process for review in rec_reviews]
        )
        to_comment = reviews.filtered("has_comment")
        if comment:
            reviews.write({"comment": comment})
        elif to_comment:
            if validate_reject == "reject" or not all(
                review.definition_id.comment_approve_default for review in to_comment
            ):
                # On an empty recordset, the base action leaves res_id unset.
                action = self.browse()._add_comment(validate_reject, reviews)
                if validate_reject == "validate":
                    action["context"]["default_comment"] = (
                        to_comment[:1].definition_id.comment_approve_default or ""
                    )
                return action
            for review in to_comment:
                review.comment = review.definition_id.comment_approve_default
        for rec, rec_reviews in to_process:
            if validate_reject == "validate":
                rec._validate_tier(rec_reviews)
            else:
                rec._rejected_tier(rec_reviews)
        done = self.browse([rec.id for rec, _rec_reviews in to_process])
        done._update_counter({"review_deleted": True})
        if validate_reject == "validate":
            message = self.env._("Review validated on %s document(s).", len(done))
        else:
            message = self.env._("Review rejected on %s document(s).", len(done))
        return self._notify_tier_validation_multi(message, len(self) - len(done))

    def _notify_tier_validation_multi(self, message, skipped):
        """Report the result, then reload the view of the selected records."""
        if skipped:
            message = self.env._(
                "%(message)s %(skipped)s skipped: nothing to do for you.",
                message=message,
                skipped=skipped,
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "warning" if skipped else "success",
                "message": message,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _get_multi_tier_reviews(self, validate_reject):
        """Return the reviews of this record that the current user validates or
        rejects from the list.

        Start from the open reviews of ``validate_tier``/``reject_tier`` and
        keep the user's ones that allow multi validation. Once an open review
        is left out (no multi validation, or someone else's), the following
        reviews approved by sequence are left out too, as ``_validate_tier``
        stops there: a later tier is never approved before it. Reviews without
        sequence do not depend on the order. Empty when the form would not
        offer the Validate/Reject buttons (rejected, or out of the states under
        validation).
        """
        self.ensure_one()
        reviews = self.env["tier.review"]
        if (
            not self.can_review
            or self.validation_status == "rejected"
            or self.hide_reviews
        ):
            return reviews
        user = self.env.user
        sequences = self._get_sequences_to_approve(user)
        bypass = validate_reject == "validate"
        candidates = self.review_ids.filtered(
            lambda r: (
                r.status in ("waiting", "pending")
                and (r.sequence in sequences or (bypass and r.approve_sequence_bypass))
            )
        )
        left_out = False
        for review in candidates.sorted("sequence"):
            if (
                review.definition_id.allow_multi_validate
                and user in review.reviewer_ids
                and not (left_out and review.approve_sequence)
            ):
                reviews |= review
            else:
                left_out = True
        return reviews
