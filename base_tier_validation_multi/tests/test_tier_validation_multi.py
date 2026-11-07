# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation

MULTI_BUTTONS = [
    "action_multi_request_validation",
    "action_multi_validate_tier",
    "action_multi_reject_tier",
]


@tagged("post_install", "-at_install")
class TestTierValidationMulti(CommonTierValidation):
    def setUp(self):
        super().setUp()
        self.multi_definition = self._create_tier_definition(
            model_id=self.tester_model.id,
            review_type="individual",
            reviewer_id=self.test_user_1.id,
            definition_domain="[('test_field', '=', 2.0)]",
            allow_multi_validate=True,
            sequence=40,
            name="Multi validation - user 1",
        )
        self.records = self.test_model.create([{"test_field": 2.0}] * 3)

    def _get_header_buttons(self, model, view_type="list"):
        """Return the button names of each header of the view, as user 1."""
        arch = model.with_user(self.test_user_1).get_view(view_type=view_type)["arch"]
        doc = etree.fromstring(arch)
        return [header.xpath("button/@name") for header in doc.findall("header")]

    def _click(self, records, method, user):
        """Click a header button on ``records`` as ``user``, in a new request
        (``need_validation`` has no dependencies)."""
        self.env.invalidate_all()
        return getattr(records.with_user(user), method)()

    def _request(self, records, user=None):
        return self._click(
            records, "action_multi_request_validation", user or self.test_user_2
        )

    def _validate(self, records, user=None):
        return self._click(
            records, "action_multi_validate_tier", user or self.test_user_1
        )

    def _reject(self, records, user=None):
        return self._click(
            records, "action_multi_reject_tier", user or self.test_user_1
        )

    def _add_comment(self, action, comment):
        """Fill the comment dialog opened by ``action`` as user 1, confirm it."""
        self.assertEqual(action["res_model"], "comment.wizard")
        model = self.env["comment.wizard"].with_user(self.test_user_1)
        wizard_form = Form(model.with_context(**action["context"]))
        wizard_form.comment = comment
        return wizard_form.save().add_comment()

    def test_01_header_buttons(self):
        """The buttons are added to the list and kanban views of the models
        with an active definition allowing multi validation, in any company."""
        self.assertEqual(self._get_header_buttons(self.test_model), [MULTI_BUTTONS])
        self.assertEqual(
            self._get_header_buttons(self.test_model, "kanban"), [MULTI_BUTTONS]
        )
        self.assertEqual(
            self._get_header_buttons(self.test_model, "form"), [["action_confirm"]]
        )
        self.assertEqual(self._get_header_buttons(self.test_model_2), [])
        # Appended to the header of the view.
        self.env["ir.ui.view"].create(
            {
                "model": self.test_model._name,
                "name": "Tester list with a header",
                "arch": """<list>
                    <header>
                        <button name="action_confirm" type="object" string="Confirm" />
                    </header>
                    <field name="test_field" />
                </list>""",
            }
        )
        self.assertEqual(
            self._get_header_buttons(self.test_model),
            [["action_confirm", *MULTI_BUTTONS]],
        )
        # A definition of another company, that user 1 cannot see, keeps them.
        other = self.multi_definition.copy({"company_id": self.other_company.id})
        self.multi_definition.with_user(self.test_user_1).action_archive()
        self.assertEqual(len(self._get_header_buttons(self.test_model)[0]), 4)
        other.allow_multi_validate = False
        self.assertEqual(
            self._get_header_buttons(self.test_model), [["action_confirm"]]
        )

    def test_02_request_and_validate_selected(self):
        """User 2 requests the validation of the selected records, user 1
        validates them all at once."""
        res = self._request(self.records)
        self.assertEqual(res["params"]["type"], "success")
        self.assertEqual(res["params"]["next"], {"type": "ir.actions.act_window_close"})
        self.assertEqual(set(self.records.mapped("validation_status")), {"pending"})
        with self.assertRaisesRegex(UserError, "needs a validation request"):
            self._request(self.records)
        with self.assertRaisesRegex(UserError, "can be reviewed by you"):
            self._validate(self.records, self.test_user_2)
        # test_record has no review: skipped.
        res = self._validate(self.records | self.test_record)
        self.assertEqual(res["params"]["type"], "warning")
        self.assertIn("1 skipped", res["params"]["message"])
        self.assertEqual(set(self.records.mapped("validation_status")), {"validated"})
        self.assertEqual(self.records.review_ids.done_by, self.test_user_1)
        self.records.with_user(self.test_user_2).action_confirm()
        self.assertEqual(set(self.records.mapped("state")), {"confirmed"})

    def test_03_only_multi_definitions_are_reviewed(self):
        """Batch validation follows the tier order and stops at the first tier
        that does not allow multi validation, which is left for the form.
        Records without a multi review are skipped."""
        self.multi_definition.write(
            {"approve_sequence": True, "approve_sequence_bypass": True, "sequence": 60}
        )
        single_definition = self.multi_definition.copy(
            {"allow_multi_validate": False, "sequence": 50, "name": "Single"}
        )
        last_definition = self.multi_definition.copy(
            {"sequence": 40, "name": "Multi validation - last tier"}
        )
        self.test_record.request_validation()  # definition_1: no multi
        self._request(self.records)
        selection = self.records | self.test_record
        self._validate(selection)
        for record in self.records:
            self.assertEqual(record.validation_status, "pending")
            status = {r.definition_id: r.status for r in record.review_ids}
            self.assertEqual(
                status,
                {
                    self.multi_definition: "approved",
                    single_definition: "pending",
                    last_definition: "waiting",
                },
            )
        self.assertEqual(self.test_record.validation_status, "pending")
        with self.assertRaisesRegex(UserError, "can be reviewed by you"):
            self._validate(selection)
        self.records[0].with_user(self.test_user_1).validate_tier()
        self.assertEqual(self.records[0].validation_status, "validated")

    def test_04_review_by_sequence(self):
        """With approve by sequence, each reviewer reviews the selected records
        in turn."""
        self.multi_definition.write({"approve_sequence": True, "sequence": 60})
        self.multi_definition.copy(
            {
                "reviewer_id": self.test_user_2.id,
                "sequence": 50,
                "name": "Multi validation - user 2",
            }
        )
        self._request(self.records, self.test_user_1)
        with self.assertRaisesRegex(UserError, "can be reviewed by you"):
            self._validate(self.records, self.test_user_2)
        self._validate(self.records)
        self.assertEqual(set(self.records.mapped("validation_status")), {"pending"})
        self.assertTrue(
            all(self.records.with_user(self.test_user_2).mapped("can_review"))
        )
        self._reject(self.records[2], self.test_user_2)
        self.assertEqual(self.records[2].validation_status, "rejected")
        self._validate(self.records[:2], self.test_user_2)
        self.assertEqual(
            set(self.records[:2].mapped("validation_status")), {"validated"}
        )

    def test_05_comments(self):
        """A definition asking for a comment: validating takes its default
        approve comment, else the comment is asked once for all documents."""
        self.multi_definition.write(
            {"has_comment": True, "comment_approve_default": "Approved"}
        )
        records = self.records | self.test_model.create({"test_field": 2.0})
        self._request(records)
        res = self._validate(records[:2])
        self.assertEqual(res["tag"], "display_notification")
        self.assertEqual(set(records[:2].review_ids.mapped("comment")), {"Approved"})
        self.assertEqual(set(records[:2].mapped("validation_status")), {"validated"})
        self.multi_definition.comment_approve_default = False
        action = self._validate(records[2])
        self.assertEqual(records[2].validation_status, "pending")
        self._add_comment(action, "Checked")
        self.assertEqual(records[2].validation_status, "validated")
        self.assertEqual(records[2].review_ids.comment, "Checked")
        self.assertEqual(records[3].validation_status, "pending")
        self._add_comment(self._reject(records[3]), "Wrong price")
        self.assertEqual(records[3].validation_status, "rejected")
        self.assertEqual(records[3].review_ids.comment, "Wrong price")
        with self.assertRaisesRegex(UserError, "can be reviewed by you"):
            self._validate(records[3])

    def test_06_reviews_without_sequence(self):
        """Without approve by sequence, the multi review is validated even when
        tiers without multi validation, or without reviewer, come first."""
        no_reviewer = self.multi_definition.copy(
            {
                "allow_multi_validate": False,
                "reviewer_id": False,
                "sequence": 60,
                "name": "No reviewer",
            }
        )
        single = self.multi_definition.copy(
            {"allow_multi_validate": False, "sequence": 50, "name": "Single"}
        )
        self._request(self.records)
        res = self._validate(self.records)
        self.assertEqual(res["params"]["type"], "success")
        for record in self.records:
            self.assertEqual(
                {r.definition_id: r.status for r in record.review_ids},
                {
                    no_reviewer: "pending",
                    single: "pending",
                    self.multi_definition: "approved",
                },
            )
