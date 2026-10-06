# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form, new_test_user, tagged

from .common import CommonTierValidation


@tagged("post_install", "-at_install")
class TierValidationAnyOfUsers(CommonTierValidation):
    """Validated by "Any of specific users": a list of users, no group."""

    def _setup_tier_definitions(self):
        self.reviewer_a = new_test_user(self.env, login="reviewer_a", name="Anna")
        self.reviewer_b = new_test_user(self.env, login="reviewer_b", name="Bert")
        self.definition = self.tier_def_obj.create(
            {
                "model_id": self.tester_model.id,
                "review_type": "users",
                "reviewer_user_ids": [(6, 0, (self.reviewer_a | self.reviewer_b).ids)],
                "definition_domain": "[('test_field', '>', 1.0)]",
            }
        )

    def test_any_listed_user_validates(self):
        record = self.test_model.create({"test_field": 2.0})
        review = record.with_user(self.test_user_2).request_validation()
        self.assertEqual(review.reviewer_ids, self.reviewer_a | self.reviewer_b)
        self.assertEqual(review.todo_by, "Anna, Bert")
        self.assertNotIn(review, self.test_user_1.review_ids)
        record.with_user(self.reviewer_b).validate_tier()
        self.assertEqual(review.status, "approved")
        self.assertEqual(review.done_by, self.reviewer_b)
        self.assertEqual(record.validation_status, "validated")

    def test_changing_the_list_updates_open_reviews(self):
        record = self.test_model.create({"test_field": 2.0})
        review = record.with_user(self.test_user_2).request_validation()
        self.definition.reviewer_user_ids = [(4, self.test_user_1.id)]
        self.assertIn(self.test_user_1, review.reviewer_ids)

    def test_four_eyes_principle(self):
        self.definition.exclude_requester = True
        record = self.test_model.create({"test_field": 2.0})
        review = record.with_user(self.reviewer_a).request_validation()
        self.assertEqual(review.reviewer_ids, self.reviewer_b)

    def test_form(self):
        with Form(self.tier_def_obj) as form:
            form.model_id = self.tester_model
            form.review_type = "users"
            form.reviewer_user_ids.add(self.reviewer_a)
        self.assertEqual(form.record.reviewer_user_ids, self.reviewer_a)
        self.assertEqual(form.record._reviewers_to_check_for_access(), self.reviewer_a)
        with Form(form.record) as form:
            form.review_type = "individual"
            form.reviewer_id = self.test_user_1
        self.assertFalse(form.record.reviewer_user_ids)
