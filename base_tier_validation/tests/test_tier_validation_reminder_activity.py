# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import fields
from odoo.orm.model_classes import add_to_registry
from odoo.tests.common import tagged

from .common import CommonTierValidation


@tagged("post_install", "-at_install")
class TestTierValidationReminderActivity(CommonTierValidation):
    """Reminders on a document with activities: one per reviewer and
    document, removed once the review no longer waits for the reviewer."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from .tier_validation_tester import TierValidationTesterActivity

        add_to_registry(cls.registry, TierValidationTesterActivity)
        cls.registry._setup_models__(cls.env.cr, ["tier.validation.tester"])
        cls.registry.init_models(
            cls.env.cr, ["tier.validation.tester"], {"models_to_check": True}
        )

    def _reminders(self, record=None):
        record = record or self.test_record
        return self.env["mail.activity"].search(
            [
                ("res_model", "=", record._name),
                ("res_id", "=", record.id),
                (
                    "activity_type_id",
                    "=",
                    self.env.ref(
                        "base_tier_validation.mail_act_tier_validation_reminder"
                    ).id,
                ),
            ]
        )

    def _remind_after(self, days):
        with freeze_time(fields.Datetime.add(fields.Datetime.now(), days=days)):
            self.tier_definition._cron_send_review_reminder()

    def _request_with_reminder(self):
        self.tier_definition.notify_reminder_delay = 3
        self.test_record.with_user(self.test_user_2.id).request_validation()
        self._remind_after(4)
        reminder = self._reminders()
        self.assertEqual(reminder.user_id, self.test_user_1)
        return reminder

    def test_validation_reminder_activity_reused(self):
        """Each run refreshes the reviewer's reminder instead of adding one."""
        reminder = self._request_with_reminder()
        self._remind_after(9)
        self._remind_after(14)
        self.assertEqual(self._reminders(), reminder)
        self.assertIn("14 days ago", reminder.note)

    def test_validation_reminder_activity_removed_when_validated(self):
        self._request_with_reminder()
        self.test_record.with_user(self.test_user_1).validate_tier()
        self.assertEqual(self.test_record.validation_status, "validated")
        self.assertFalse(self._reminders())

    def test_validation_reminder_activity_removed_when_rejected(self):
        self._request_with_reminder()
        self.test_record.with_user(self.test_user_1).reject_tier()
        self.assertFalse(self._reminders())

    def test_validation_reminder_activity_removed_on_restart(self):
        self._request_with_reminder()
        self.test_record.restart_validation()
        self.assertFalse(self.test_record.review_ids)
        self.assertFalse(self._reminders())

    def test_validation_reminder_activity_removed_for_old_reviewer(self):
        """A reviewer replaced on the review loses the reminder."""
        self._request_with_reminder()
        review = self.test_record.review_ids
        review.reviewer_ids = self.test_user_3_multi_company
        self.assertFalse(self._reminders())

    def test_validation_reminder_activity_removed_after_recompute(self):
        """A reviewer replaced through the definition, which recomputes the
        review without write(), loses the reminder at the next run."""
        self._request_with_reminder()
        self.tier_definition.reviewer_id = self.test_user_2
        self.assertEqual(self.test_record.review_ids.reviewer_ids, self.test_user_2)
        self._remind_after(9)
        self.assertEqual(self._reminders().user_id, self.test_user_2)

    def test_validation_reminder_activity_duplicates_removed(self):
        """Duplicates from before the fix are removed at the next run."""
        reminder = self._request_with_reminder()
        reminder.copy()
        reminder.copy()
        self._remind_after(9)
        self.assertEqual(len(self._reminders()), 1)

    def test_validation_reminder_activity_kept_for_other_pending_review(self):
        """The reminder stays while the reviewer has another pending review
        on the same document."""
        reminder = self._request_with_reminder()
        other = self.env["tier.review"].create(
            {
                "model": self.test_record._name,
                "res_id": self.test_record.id,
                "definition_id": self.definition_1.id,
                "status": "pending",
            }
        )
        other.reviewer_ids = self.test_user_1
        self.test_record.review_ids.filtered(lambda r: r != other).status = "approved"
        self.assertEqual(self._reminders(), reminder)

    def test_validation_reminder_message_for_several_reviewers(self):
        """A review with several reviewers is reminded in the chatter."""
        self.tier_definition.notify_reminder_delay = 3
        self.test_record.with_user(self.test_user_2.id).request_validation()
        self.test_record.review_ids.reviewer_ids = self.test_user_1 + self.test_user_2
        subtype = self.env.ref("base_tier_validation.mt_tier_validation_reminder")
        self._remind_after(4)
        self.assertFalse(self._reminders())
        self.assertTrue(
            self.env["mail.message"].search(
                [
                    ("model", "=", self.test_record._name),
                    ("res_id", "=", self.test_record.id),
                    ("subtype_id", "=", subtype.id),
                ]
            )
        )

    def test_validation_reminder_by_message(self):
        """Remind by message: no activity, a message on the document."""
        self.tier_definition.notify_reminder_type = "message"
        self.tier_definition.notify_reminder_delay = 3
        self.test_record.with_user(self.test_user_2.id).request_validation()
        subtype = self.env.ref("base_tier_validation.mt_tier_validation_reminder")
        self._remind_after(4)
        self.assertFalse(self._reminders())
        self.assertTrue(
            self.env["mail.message"].search(
                [
                    ("model", "=", self.test_record._name),
                    ("res_id", "=", self.test_record.id),
                    ("subtype_id", "=", subtype.id),
                ]
            )
        )
