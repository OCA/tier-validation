# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form, new_test_user, tagged

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation


@tagged("post_install", "-at_install")
class TestForwardAnyOfUsers(CommonTierValidation):
    def _setup_tier_definitions(self):
        self.colleague = new_test_user(self.env, login="colleague", name="Clara")
        self.tier_def_obj.create(
            {
                "model_id": self.tester_model.id,
                "review_type": "users",
                "reviewer_user_ids": [(6, 0, (self.test_user_2 | self.colleague).ids)],
                "definition_domain": "[('test_field', '>', 1.0)]",
                "has_forward": True,
            }
        )

    def test_forward_keeps_only_the_new_reviewer(self):
        """A forwarded review is for that user alone, not for the whole list."""
        record = self.test_model.create({"test_field": 2.0})
        record.with_user(self.test_user_1).request_validation()
        record = record.with_user(self.test_user_2)
        res = record.forward_tier()
        wizard = Form(
            self.env["tier.validation.forward.wizard"]
            .with_user(self.test_user_2)
            .with_context(**res["context"])
        )
        wizard.forward_reviewer_id = self.test_user_1
        wizard.forward_description = "Please have a look"
        wizard.save().add_forward()
        record.invalidate_recordset()
        forwarded = record.review_ids.filtered(lambda r: not r.definition_id)
        self.assertEqual(forwarded.reviewer_ids, self.test_user_1)
