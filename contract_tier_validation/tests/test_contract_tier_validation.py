# Copyright 2026 bosd
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestContractTierValidation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.partner = cls.env["res.partner"].create({"name": "Tiered customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Service", "type": "service"}
        )
        cls.contract = cls.env["contract.contract"].create(
            {
                "name": "Contract under review",
                "partner_id": cls.partner.id,
                "company_id": cls.company.id,
                "contract_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "name": "Service",
                            "quantity": 1,
                            "price_unit": 100,
                            "date_start": "2026-01-01",
                        },
                    )
                ],
            }
        )
        cls.line = cls.contract.contract_line_ids[0]

    # --- the mixin is wired up -------------------------------------------

    def test_contract_carries_the_tier_validation_mixin(self):
        self.assertIn("review_ids", self.contract._fields)
        self.assertEqual(self.contract._state_from, ["draft"])
        self.assertEqual(self.contract._state_to, ["active"])

    def test_contract_is_selectable_on_a_tier_definition(self):
        """contract.contract must appear in the tier definition model list.

        Applying the mixin is not enough: the definition's ``model_id`` is
        restricted to the models each glue module registers here, so without
        this a reviewer cannot pick Contract when creating a tier definition.
        """
        res = self.env["tier.definition"]._get_tier_validation_model_names()
        self.assertIn("contract.contract", res)

    def test_system_written_fields_are_excepted(self):
        exceptions = self.contract._get_under_validation_exceptions()
        for name in ("recurring_next_date", "date_end", "last_date_invoiced"):
            self.assertIn(name, exceptions)

    def test_the_after_validation_gate_stays_off_by_default(self):
        """Extending the wrong list freezes every field of every contract.

        The after-validation check only engages once something is configured,
        so this module must not put anything there just by existing. An
        administrator turns it on with a Tier Validation Exception.
        """
        self.assertFalse(
            self.contract._get_validation_exceptions(add_base_exceptions=False),
            "No Tier Validation Exception is configured, so nothing should "
            "switch on the after-validation lock",
        )

    # --- the line lock ----------------------------------------------------

    def _validate(self):
        """Put the contract in the state the lock cares about."""
        self.contract.state = "active"
        self.contract.invalidate_recordset()

    def test_lines_are_not_locked_before_validation(self):
        self.assertFalse(self.contract._is_locked_by_validation())
        self.line.price_unit = 200
        self.assertEqual(self.line.price_unit, 200)

    def test_lock_needs_a_passed_validation(self):
        """Being active is not enough; the review has to have passed."""
        self._validate()
        self.assertNotEqual(self.contract.validation_status, "validated")
        self.assertFalse(self.contract._is_locked_by_validation())

    def test_lock_is_off_when_the_company_says_so(self):
        self.company.contract_lock_lines_after_validation = False
        self._validate()
        self.assertFalse(self.contract._is_locked_by_validation())

    def test_machine_fields_stay_writable(self):
        """Whatever the lock does, it must not stop the invoicing run."""
        exceptions = self.line._get_line_lock_exceptions()
        self.assertIn("last_date_invoiced", exceptions)
        self.assertIn("recurring_next_date", exceptions)

    def test_successor_fields_are_excepted_when_installed(self):
        """Renewal actions are lifecycle, not terms, so they stay allowed."""
        exceptions = self.line._get_line_lock_exceptions()
        for name in ("date_end", "is_auto_renew", "is_canceled"):
            if name in self.line._fields:
                self.assertIn(name, exceptions)

    def test_exceptions_never_name_a_field_that_does_not_exist(self):
        """The list degrades when contract_line_successor is absent."""
        for name in self.line._get_line_lock_exceptions():
            self.assertIn(name, self.line._fields)

    def _validated_contract(self):
        """A contract that has really been through its review chain."""
        reviewer = self.env["res.users"].create(
            {
                "name": "Reviewer",
                "login": f"tier_reviewer_{self._testMethodName}",
                "group_ids": [
                    (4, self.env.ref("base.group_user").id),
                    (4, self.env.ref("account.group_account_invoice").id),
                ],
            }
        )
        self.env["tier.definition"].create(
            {
                "model_id": self.env["ir.model"]._get("contract.contract").id,
                "review_type": "individual",
                "reviewer_id": reviewer.id,
                "definition_domain": "[]",
            }
        )
        contract = self.env["contract.contract"].create(
            {
                "name": "Reviewed contract",
                "partner_id": self.partner.id,
                "company_id": self.company.id,
                "contract_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "Service",
                            "quantity": 1,
                            "price_unit": 100,
                            "date_start": "2026-01-01",
                        },
                    )
                ],
            }
        )
        contract.request_validation()
        contract.with_user(reviewer).validate_tier()
        contract.invalidate_recordset()
        self.assertEqual(contract.validation_status, "validated")
        return contract

    def test_locked_contract_refuses_a_term_change(self):
        contract = self._validated_contract()
        self.assertTrue(contract._is_locked_by_validation())
        with self.assertRaises(ValidationError):
            contract.contract_line_ids[0].price_unit = 999

    def test_locked_contract_still_takes_the_excepted_fields(self):
        """The invoicing run writes these, and it must keep working."""
        contract = self._validated_contract()
        line = contract.contract_line_ids[0]
        line.recurring_next_date = "2026-03-01"
        self.assertEqual(str(line.recurring_next_date), "2026-03-01")

    def test_locked_contract_refuses_a_new_line(self):
        contract = self._validated_contract()
        with self.assertRaises(ValidationError):
            self.env["contract.line"].create(
                {
                    "contract_id": contract.id,
                    "product_id": self.product.id,
                    "name": "Smuggled in",
                    "quantity": 1,
                    "price_unit": 1,
                    "date_start": "2026-01-01",
                }
            )

    def test_an_unvalidated_contract_can_lose_a_line(self):
        """The lock must not get in the way before there is anything to lock."""
        self.line.unlink()
        self.assertFalse(self.contract.contract_line_ids)

    def test_locked_contract_refuses_to_lose_a_line(self):
        contract = self._validated_contract()
        with self.assertRaises(ValidationError):
            contract.contract_line_ids[0].unlink()

    def test_the_company_switch_unlocks_the_lines(self):
        contract = self._validated_contract()
        self.company.contract_lock_lines_after_validation = False
        contract.invalidate_recordset()
        contract.contract_line_ids[0].price_unit = 999
        self.assertEqual(contract.contract_line_ids[0].price_unit, 999)

    def test_an_already_active_contract_is_left_alone(self):
        """_activate_if_validated only looks at contracts still in draft."""
        contract = self._validated_contract()
        self.assertEqual(contract.state, "active")
        contract._activate_if_validated()
        self.assertEqual(contract.state, "active")

    def test_the_notification_subtypes_resolve(self):
        self.assertTrue(self.contract._get_to_validate_message_name())
        for xmlid in (
            self.contract._get_requested_notification_subtype(),
            self.contract._get_accepted_notification_subtype(),
            self.contract._get_rejected_notification_subtype(),
        ):
            self.assertTrue(self.env.ref(xmlid), xmlid)

    def test_skip_validation_check_context_bypasses_the_lock(self):
        """The escape hatch other modules use for their own actions."""
        self.line.with_context(skip_validation_check=True).price_unit = 123
        self.assertEqual(self.line.price_unit, 123)

    def test_the_last_approval_activates_the_contract(self):
        """No second click: accepting the final review starts the contract."""
        reviewer = self.env["res.users"].create(
            {
                "name": "Reviewer",
                "login": "tier_reviewer",
                "group_ids": [
                    (4, self.env.ref("base.group_user").id),
                    (4, self.env.ref("account.group_account_invoice").id),
                ],
            }
        )
        self.env["tier.definition"].create(
            {
                "model_id": self.env["ir.model"]._get("contract.contract").id,
                "review_type": "individual",
                "reviewer_id": reviewer.id,
                "definition_domain": "[]",
            }
        )
        contract = self.env["contract.contract"].create(
            {"name": "Auto activated", "partner_id": self.partner.id}
        )
        self.assertEqual(contract.state, "draft")
        contract.request_validation()
        contract.invalidate_recordset()
        self.assertEqual(contract.state, "draft", "Still draft while pending")
        contract.with_user(reviewer).validate_tier()
        contract.invalidate_recordset()
        self.assertEqual(contract.validation_status, "validated")
        self.assertEqual(
            contract.state, "active", "The accepted review should activate it"
        )

    def test_a_contract_with_no_reviews_is_left_alone(self):
        """Nothing to approve means nothing to activate automatically."""
        contract = self.env["contract.contract"].create(
            {"name": "No tiers", "partner_id": self.partner.id}
        )
        contract._activate_if_validated()
        self.assertEqual(contract.state, "draft")

    def test_the_cron_can_still_report_a_failure_once_the_gate_is_armed(self):
        """Arming the second gate must not break the error reporting.

        An administrator freezing the template switches the after-validation
        check on for every field. If the recurring-invoice cron could no
        longer record why a contract failed to invoice, the reporting would
        break exactly when it is needed.
        """
        exceptions = self.contract._get_after_validation_exceptions()
        for name in self.contract._get_system_written_fields():
            self.assertIn(
                name,
                exceptions,
                f"{name} is written by the system and must survive the gate",
            )

    def test_system_written_fields_skip_what_is_not_installed(self):
        for name in self.contract._get_system_written_fields():
            self.assertIn(name, self.contract._fields)
