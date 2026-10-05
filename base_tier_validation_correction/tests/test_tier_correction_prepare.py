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
