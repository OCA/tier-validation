# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import tagged

from .common import CommonTierValidation


@tagged("post_install", "-at_install")
class TestTierOrder(CommonTierValidation):
    def test_same_sequence_in_creation_order(self):
        """Two sequential definitions with the same sequence give their tiers
        in creation order, whatever order the database returns them in."""
        first, second = self.tier_def_obj.create(
            [
                {
                    "model_id": self.tester_model.id,
                    "review_type": "individual",
                    "reviewer_id": user.id,
                    "definition_domain": "[('test_field', '=', 7.0)]",
                    "approve_sequence": True,
                    "sequence": 30,
                }
                for user in (self.test_user_1, self.test_user_2)
            ]
        )
        # Rewriting the first one stores it after the second in the table.
        first.name = "First, rewritten"
        self.env.flush_all()
        record = self.test_model.create({"test_field": 7.0})
        reviews = record.request_validation().filtered(
            lambda review: review.definition_id in first | second
        )
        self.assertEqual(
            reviews.sorted("sequence").mapped("definition_id"), first | second
        )
