# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.orm.model_classes import add_to_registry

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation


class TestTierCorrectionDocumentDomain(CommonTierValidation):
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

    def _correction(self, document_domain):
        return self.env["tier.correction"].create(
            {
                "name": "Correction",
                "model_id": self.tester_model.id,
                "document_domain": document_domain,
                "new_reviewer_ids": [Command.set(self.test_user_2.ids)],
            }
        )

    def test_document_domain_filters_documents(self):
        """Only documents matching the filter, and with open reviews, are
        listed."""
        other = self.test_model.create({"test_field": 1.0})
        (self.test_record | other).with_user(self.test_user_2).request_validation()
        correction = self._correction(str([("id", "=", other.id)]))
        correction.search_document()
        self.assertEqual(correction.item_ids.resource_ref, other)
        correction = self._correction("[]")
        correction.search_document()
        self.assertEqual(len(correction.item_ids), 2)

    def test_document_domain_with_dates(self):
        """The filter is evaluated like a view domain, dates included."""
        self.test_record.with_user(self.test_user_2).request_validation()
        correction = self._correction(
            "[('create_date', '>=', "
            "(context_today() - relativedelta(days=1)).strftime('%Y-%m-%d'))]"
        )
        correction.search_document()
        self.assertEqual(correction.item_ids.resource_ref, self.test_record)

    def test_change_reviewer_targets_the_document(self):
        """Opened from a document, the correction filters on that document."""
        action = self.test_record.view_tier_correction()
        self.assertEqual(
            action["context"]["default_document_domain"],
            str([("id", "=", self.test_record.id)]),
        )
