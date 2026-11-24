# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests.common import tagged

from .common import CommonTierValidation


@tagged("post_install", "-at_install")
class TestTierDefinitionChange(CommonTierValidation):
    """Changing who reviews on a tier definition: open reviews follow it and
    their documents get a note, closed reviews keep who was asked."""

    def _notes(self, record):
        return record.message_ids.filtered(
            lambda m: m.subtype_id == self.env.ref("mail.mt_note")
            and "tier definition" in (m.body or "")
        )

    def _to_group(self, definitions):
        definitions.write(
            {"review_type": "group", "reviewer_group_id": self.test_group.id}
        )

    def test_closed_review_keeps_reviewers(self):
        self.test_record.with_user(self.test_user_2).request_validation()
        self.test_record.with_user(self.test_user_1).validate_tier()
        review = self.test_record.review_ids
        self.assertEqual(review.status, "approved")
        self.assertEqual(review.todo_by, "John")
        self._to_group(self.definition_1)
        self.assertEqual(review.reviewer_ids, self.test_user_1)
        self.assertEqual(review.todo_by, "John")
        self.assertFalse(self._notes(self.test_record))

    def test_closed_review_keeps_group_members(self):
        """Members added to the group later were not asked to review."""
        self._to_group(self.definition_1)
        self.test_record.with_user(self.test_user_2).request_validation()
        self.test_record.with_user(self.test_user_1).validate_tier()
        review = self.test_record.review_ids
        self.test_group.user_ids = [Command.link(self.test_user_3_multi_company.id)]
        self.assertEqual(review.reviewer_ids, self.test_user_1 | self.test_user_2)

    def test_open_review_follows_definition_with_note(self):
        self.test_record.with_user(self.test_user_2).request_validation()
        review = self.test_record.review_ids
        self._to_group(self.definition_1)
        self.assertEqual(review.reviewer_ids, self.test_user_1 | self.test_user_2)
        note = self._notes(self.test_record)
        self.assertEqual(len(note), 1)
        self.assertIn("John", note.body)
        self.assertIn("Group TestGroup", note.body)

    def test_one_note_per_document(self):
        other = self._create_tier_definition(
            model_id=self.tester_model.id,
            review_type="individual",
            reviewer_id=self.test_user_2.id,
            definition_domain="[('test_field', '=', 1.0)]",
            sequence=40,
        )
        self.test_record.with_user(self.test_user_2).request_validation()
        self.assertEqual(len(self.test_record.review_ids), 2)
        (self.definition_1 | other).reviewer_id = self.test_user_3_multi_company
        note = self._notes(self.test_record)
        self.assertEqual(len(note), 1)
        self.assertEqual(note.body.count("<li>"), 2)

    def test_no_note_without_reviewer_change(self):
        self.test_record.with_user(self.test_user_2).request_validation()
        self.definition_1.write({"name": "Renamed", "sequence": 50})
        # Same reviewer again: nothing changes for the review
        self.definition_1.reviewer_id = self.test_user_1
        self.assertFalse(self._notes(self.test_record))

    def test_no_note_without_chatter(self):
        """Documents without chatter follow the definition, without note."""
        self.test_record_2.with_user(self.test_user_2).request_validation()
        review = self.test_record_2.review_ids.filtered(
            lambda r: r.definition_id == self.definition_7
        )
        self.assertTrue(review)
        self.definition_7.reviewer_id = self.test_user_2
        self.assertEqual(review.reviewer_ids, self.test_user_2)
