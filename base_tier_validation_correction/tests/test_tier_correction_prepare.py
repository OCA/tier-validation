# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.exceptions import UserError
from odoo.orm.model_classes import add_to_registry

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation


class TestTierCorrectionPrepare(CommonTierValidation):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from .tier_validation_tester import TierValidationTester

        add_to_registry(cls.registry, TierValidationTester)
        cls.registry._setup_models__(cls.env.cr, ["tier.validation.tester"])
        cls.registry.init_models(
            cls.env.cr,
            ["tier.validation.tester"],
            {"models_to_check": True},
        )

    def test_prepare_without_matching_documents(self):
        """Preparing a correction that finds nothing is refused."""
        self.test_record.with_user(self.test_user_2).request_validation()
        correction = self.env["tier.correction"].create(
            {
                "name": "Correction",
                "model_id": self.tester_model.id,
                # The document's review is assigned to test_user_1.
                "old_reviewer_ids": [Command.set(self.test_user_2.ids)],
                "new_reviewer_ids": [Command.set(self.test_user_2.ids)],
            }
        )
        with self.assertRaises(UserError):
            correction.action_prepare()
        self.assertEqual(correction.state, "draft")

    def test_warn_new_reviewers_without_access(self):
        """Choosing a new reviewer who cannot read the model warns."""
        # Only internal users can read the tester model.
        self.env["ir.model.access"].search(
            [("model_id", "=", self.tester_model.id)]
        ).group_id = self.env.ref("base.group_user")
        self.env["ir.model.access"].call_cache_clearing_methods()
        portal = self.env["res.users"].create(
            {
                "name": "No access",
                "login": "no_access_reviewer",
                "group_ids": [Command.set(self.env.ref("base.group_portal").ids)],
            }
        )
        correction = self.env["tier.correction"].new(
            {"model_id": self.tester_model.id, "new_reviewer_ids": portal.ids}
        )
        res = correction._onchange_warn_new_reviewers_access()
        self.assertIn("No access", res["warning"]["message"])
        correction.new_reviewer_ids = self.test_user_2
        self.assertFalse(correction._onchange_warn_new_reviewers_access())
        item = self.env["tier.correction.item"].new(
            {"res_model": self.tester_model.model, "new_reviewer_ids": portal.ids}
        )
        res = item._onchange_warn_new_reviewers_access()
        self.assertIn("No access", res["warning"]["message"])
        # Nothing to check without new reviewers.
        correction.new_reviewer_ids = False
        self.assertFalse(correction._onchange_warn_new_reviewers_access())
        item.new_reviewer_ids = False
        self.assertFalse(item._onchange_warn_new_reviewers_access())
