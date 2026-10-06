# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from .common import CommonTierValidation


@tagged("post_install", "-at_install")
class TestTierRestart(CommonTierValidation):
    def setUp(self):
        super().setUp()
        self.test_record.with_user(self.test_user_2).request_validation()
        self.assertIn(self.tier_definition, self.test_record.review_ids.definition_id)

    def _can_restart(self, user):
        return self.test_record.with_user(user).can_restart_validation

    def test_restart_allowed_by_default(self):
        self.assertTrue(self._can_restart(self.test_user_2))
        self.test_record.with_user(self.test_user_2).restart_validation()
        self.assertFalse(self.test_record.review_ids)

    def test_restart_not_allowed(self):
        """A tier that does not allow a restart blocks it, except for tier
        validation administrators."""
        self.tier_definition.allow_restart = False
        self.assertFalse(self._can_restart(self.test_user_2))
        with self.assertRaises(UserError):
            self.test_record.with_user(self.test_user_2).restart_validation()
        self.assertTrue(self.test_record.review_ids)
        manager = new_test_user(
            self.env,
            login="tier_manager",
            groups="base.group_user,base_tier_validation.group_tier_validation_manager",
        )
        self.assertTrue(self._can_restart(manager))
        # Settings administrators are tier validation administrators too.
        admin = self.env.ref("base.user_admin")
        self.assertTrue(self._can_restart(admin))
        self.test_record.with_user(admin).restart_validation()
        self.assertFalse(self.test_record.review_ids)

    def test_restart_limited_to_groups(self):
        """Only members of one of the tier's groups, implied ones included,
        can restart."""
        group = self.env["res.groups"].create({"name": "Restarters"})
        implying = self.env["res.groups"].create(
            {"name": "Restart managers", "implied_ids": [Command.link(group.id)]}
        )
        self.tier_definition.restart_group_ids = group
        self.assertFalse(self._can_restart(self.test_user_2))
        self.test_user_2.group_ids |= group
        self.assertTrue(self._can_restart(self.test_user_2))
        manager = new_test_user(self.env, login="restart_manager")
        manager.group_ids |= implying
        self.assertTrue(self._can_restart(manager))

    def test_restart_groups_are_internal(self):
        """The portal and public roles are not offered as restart groups."""
        domain = (
            self.env["tier.definition"]
            ._fields["restart_group_ids"]
            .domain(self.env["tier.definition"])
        )
        allowed = self.env["res.groups"].search(domain)
        roles = self.env.ref("base.group_portal") | self.env.ref("base.group_public")
        self.assertFalse(roles & allowed)
        self.assertIn(self.env.ref("base.group_user"), allowed)

    def test_other_tiers_do_not_count(self):
        """A rule on a tier without review on the document has no effect."""
        other = self.tier_definition.copy({"definition_domain": "[('id', '=', 0)]"})
        other.allow_restart = False
        self.assertNotIn(other, self.test_record.review_ids.definition_id)
        self.assertTrue(self._can_restart(self.test_user_2))
