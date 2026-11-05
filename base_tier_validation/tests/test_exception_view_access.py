# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, new_test_user


class TestTierValidationExceptionViewAccess(TransactionCase):
    """``tier.validation.exception.field_ids`` is a Many2many to
    ``ir.model.fields``. The model is readable by ``base.group_user`` (so
    the validation logic can check exceptions), so exposing ``field_ids`` in
    its views without a ``groups=`` gate makes a non-Settings user who opens
    one of those views hit an Access Error on ``ir.model.fields`` ("You are
    not allowed to access 'Fields' (ir.model.fields) records"). The field is
    now gated to ``base.group_system``; this test guards that."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Plain internal user: base.group_user, NOT Settings.
        cls.basic_user = new_test_user(
            cls.env, login="tv_exc_basic", groups="base.group_user"
        )

    def test_field_ids_hidden_from_non_system_user(self):
        model = self.env["tier.validation.exception"].with_user(self.basic_user)
        for view_type in ("list", "form", "search"):
            arch = model.get_view(view_type=view_type)["arch"]
            self.assertNotIn(
                "field_ids",
                arch,
                f"field_ids (-> ir.model.fields) leaked into the {view_type} "
                f"view for a non-Settings user; it must be gated with groups=",
            )

    def test_field_ids_visible_to_system_user(self):
        # A Settings user (has ir.model.fields access) still gets the field.
        model = self.env["tier.validation.exception"]
        for view_type in ("list", "form"):
            arch = model.get_view(view_type=view_type)["arch"]
            self.assertIn(
                "field_ids",
                arch,
                f"field_ids should remain visible to Settings users in the "
                f"{view_type} view",
            )
