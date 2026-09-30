# Copyright 2026 OCA / @bosd
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.fields import Domain
from odoo.tests.common import tagged

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation


@tagged("post_install", "-at_install")
class TierValidationBoard(CommonTierValidation):
    def setUp(self):
        super().setUp()
        # Trigger a review on the standard test fixture so the board
        # always has at least one record to render.
        self.test_record.with_user(self.test_user_2.id).request_validation()
        self.review = self.env["tier.review"].search(
            Domain("res_id", "=", self.test_record.id)
            & Domain("model", "=", self.test_record._name),
            limit=1,
        )
        self.assertTrue(self.review)

    def test_related_model_instance_compute(self):
        """The board's Reference + Char computes resolve cleanly off a
        real tier review."""
        review = self.review
        self.assertEqual(review.res_name, self.test_record.display_name)
        self.assertEqual(review.related_model_instance._name, self.test_record._name)
        self.assertEqual(review.related_model_instance.id, self.test_record.id)

    def test_selection_related_model_instance(self):
        """The Reference selection only exposes tier-validated models,
        not every model in the DB."""
        selection = self.env["tier.review"]._selection_related_model_instance()
        models = {m for m, _name in selection}
        expected = set(self.env["tier.definition"]._get_tier_validation_model_names())
        self.assertEqual(models, expected)
        # Sanity: at least the standard tester model is in there.
        self.assertIn(self.test_record._name, models)

    def test_open_origin(self):
        """The board's `Open` button returns an act_window pointing at
        the underlying validated record."""
        action = self.review.open_origin()
        self.assertEqual(action["res_model"], self.test_record._name)
        self.assertEqual(action["res_id"], self.test_record.id)
        self.assertEqual(action["view_mode"], "form")

    def test_search_filters_by_user_acl(self):
        """The `_search` override hides reviews whose underlying record
        the current user cannot read. The standard tester model has a
        public ACL so test_user_2 sees everything; revoke that ACL and
        the review should drop out of the board for them."""
        # Sanity: test_user_2 can see the review with the default ACL.
        visible = (
            self.env["tier.review"]
            .with_user(self.test_user_2)
            .search(Domain("id", "=", self.review.id))
        )
        self.assertEqual(visible, self.review)
        # Restrict the model's ACL to admins; test_user_2 loses access.
        self.env["ir.model.access"].search(
            Domain("model_id", "=", self.tester_model.id)
        ).write({"group_id": self.env.ref("base.group_system").id})
        self.env["ir.model.access"].call_cache_clearing_methods()
        hidden = (
            self.env["tier.review"]
            .with_user(self.test_user_2)
            .search(Domain("id", "=", self.review.id))
        )
        self.assertFalse(hidden)
