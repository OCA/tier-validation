# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import re
from datetime import timedelta

from odoo.tests.common import tagged
from odoo.tools.misc import file_path

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation


@tagged("post_install", "-at_install")
class TestTierValidationDigest(CommonTierValidation):
    """Verify that ``tier.review`` rows surface as digest KPI counts.

    Reuses ``CommonTierValidation`` so the same test users / definitions /
    test record model are available. The base set-up provides:

    - ``definition_1`` -- individual, reviewer ``test_user_1``, no
      approve_sequence, matches ``test_field == 1.0``.
    - ``definition_2`` -- individual, reviewer ``test_user_1``,
      approve_sequence + notify_on_pending=False, matches
      ``test_field > 3.0``.
    - ``definition_3`` -- individual, reviewer ``test_user_2``,
      approve_sequence + notify_on_pending=True, matches
      ``test_field > 3.0``.

    Reviews created by ``request_validation`` start as ``waiting`` on
    origin/19.0; this module is allowed to assume that and explicitly
    promotes the available review via ``_update_review_status`` to keep
    the test set-up independent of the (separate) auto-promote fix.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Digest = cls.env["digest.digest"]

    def _build_digest(self, name="Tier Validation Test Digest"):
        return self.Digest.create(
            {
                "name": name,
                "kpi_tier_validation_pending": True,
                "kpi_tier_validation_waiting": True,
                "kpi_tier_validation_late": True,
                "kpi_tier_validation_validated_period": True,
                "kpi_tier_validation_pending_team": True,
            }
        )

    def test_pending_kpi_counts_only_my_reviews(self):
        """``kpi_tier_validation_pending_value`` reflects reviews that the
        recipient user is allowed to act on right now."""
        test_record = self.test_model.create({"test_field": 1.0})
        reviews = test_record.request_validation()
        self.assertTrue(reviews)
        reviews._update_review_status()
        digest = self._build_digest()

        # test_user_1 is the reviewer of definition_1 -- they should see 1.
        self.assertEqual(
            digest.with_user(self.test_user_1).kpi_tier_validation_pending_value,
            1,
        )
        # test_user_2 is not on any matching definition -- they should see 0.
        self.assertEqual(
            digest.with_user(self.test_user_2).kpi_tier_validation_pending_value,
            0,
        )

    def test_waiting_kpi_counts_queued_reviews(self):
        """When ``approve_sequence`` is on, the next reviewer's pending
        tier keeps the subsequent reviewer with a waiting tier. That tier
        is counted in the queued KPI."""
        test_record = self.test_model.create({"test_field": 3.5})
        reviews = test_record.request_validation()
        reviews._update_review_status()
        # ``request_validation`` iterates definitions in ``sequence desc``,
        # so definition_2 (def_seq=20, user_1) becomes tier.review.sequence=1
        # and is promoted to pending; definition_3 (def_seq=10, user_2)
        # becomes tier.review.sequence=2 and stays waiting.
        waiting = reviews.filtered(lambda r: r.status == "waiting")
        self.assertEqual(len(waiting), 1)
        self.assertIn(self.test_user_2, waiting.reviewer_ids)
        digest = self._build_digest()

        self.assertEqual(
            digest.with_user(self.test_user_2).kpi_tier_validation_waiting_value,
            1,
        )
        self.assertEqual(
            digest.with_user(self.test_user_1).kpi_tier_validation_waiting_value,
            0,
        )

    def test_validated_period_kpi_respects_digest_window(self):
        """Approved reviews done by the recipient inside the digest period
        bracket are counted; approvals outside the bracket are not."""
        test_record = self.test_model.create({"test_field": 1.0})
        reviews = test_record.request_validation()
        reviews._update_review_status()
        test_record.with_user(self.test_user_1).validate_tier()
        approved = reviews.filtered(lambda r: r.status == "approved")
        self.assertEqual(len(approved), 1)
        self.assertTrue(approved.reviewed_date)
        self.assertEqual(approved.done_by, self.test_user_1)

        digest = self._build_digest()
        in_window = digest.with_user(self.test_user_1).with_context(
            start_datetime=approved.reviewed_date - timedelta(days=1),
            end_datetime=approved.reviewed_date + timedelta(days=1),
        )
        out_window = digest.with_user(self.test_user_1).with_context(
            start_datetime=approved.reviewed_date - timedelta(days=10),
            end_datetime=approved.reviewed_date - timedelta(days=5),
        )
        self.assertEqual(in_window.kpi_tier_validation_validated_period_value, 1)
        self.assertEqual(out_window.kpi_tier_validation_validated_period_value, 0)

    def test_team_pending_kpi_for_manager(self):
        """The team-pending count goes up by one for each new pending
        review across the company. Uses a delta to avoid coupling to the
        suite's overall ``tier.review`` row count.
        """
        digest = self._build_digest()
        digest.invalidate_recordset(["kpi_tier_validation_pending_team_value"])
        baseline = digest.kpi_tier_validation_pending_team_value
        test_record = self.test_model.create({"test_field": 1.0})
        reviews = test_record.request_validation()
        reviews._update_review_status()
        digest.invalidate_recordset(["kpi_tier_validation_pending_team_value"])
        self.assertEqual(
            digest.kpi_tier_validation_pending_team_value - baseline,
            1,
        )

    def test_default_pending_tile_enabled_on_new_digests(self):
        """The "pending for you" tile must be enabled out of the box on a
        freshly-created digest, so users see it on their next periodic
        email without having to revisit Settings.
        """
        digest = self.Digest.create({"name": "fresh digest"})
        self.assertTrue(digest.kpi_tier_validation_pending)
        # Other tiles stay opt-in (False by default).
        self.assertFalse(digest.kpi_tier_validation_waiting)
        self.assertFalse(digest.kpi_tier_validation_late)
        self.assertFalse(digest.kpi_tier_validation_validated_period)

    def test_post_init_hook_enables_pending_on_existing_digests(self):
        """The post-init hook is what closes the gap for digests that
        existed before this module was installed. Run it explicitly and
        confirm a previously-False pending toggle flips to True without
        touching the other toggles.
        """
        from ..hooks import _post_init_hook

        digest = self.Digest.create(
            {
                "name": "pre-existing digest",
                "kpi_tier_validation_pending": False,
                "kpi_tier_validation_waiting": False,
                "kpi_tier_validation_validated_period": False,
            }
        )
        self.assertFalse(digest.kpi_tier_validation_pending)
        _post_init_hook(self.env)
        digest.invalidate_recordset()
        self.assertTrue(digest.kpi_tier_validation_pending)
        # Other toggles untouched.
        self.assertFalse(digest.kpi_tier_validation_waiting)
        self.assertFalse(digest.kpi_tier_validation_validated_period)

    def test_kpis_actions_open_the_review_board(self):
        """Each tile links to an action of the review board.

        The digest builds the link as ``/odoo/action-<token>``, so the menu
        must come as a query parameter (``?menu_id=``), not glued on with
        ``&`` -- that made the "Open Report" link lead nowhere.
        """
        digest = self._build_digest()
        actions = digest._compute_kpis_actions(self.env.company, self.env.user)
        menu = self.env.ref("spreadsheet_dashboard.spreadsheet_dashboard_menu_root")
        board = "base_tier_validation_board"
        digest_module = "tier_validation_digest"
        expected = {
            "kpi_tier_validation_pending": (
                f"{board}.open_my_tier_reviews",
                "search_default_state_pending",
            ),
            "kpi_tier_validation_waiting": (
                f"{digest_module}.action_my_waiting_tier_reviews",
                "search_default_state_waiting",
            ),
            "kpi_tier_validation_late": (
                f"{digest_module}.action_my_late_tier_reviews",
                "search_default_late",
            ),
            "kpi_tier_validation_validated_period": (
                f"{digest_module}.action_my_validated_tier_reviews",
                "search_default_state_approved",
            ),
            "kpi_tier_validation_pending_team": (
                f"{board}.open_boards_tier_reviews",
                "search_default_state_pending",
            ),
        }
        for kpi, (xmlid, default_filter) in expected.items():
            action_xmlid, query = actions[kpi].split("?")
            self.assertEqual(action_xmlid, xmlid)
            self.assertEqual(query, f"menu_id={menu.id}")
            self.assertIn(default_filter, self.env.ref(xmlid).context)

    def test_late_kpi_follows_the_late_threshold(self):
        """Late uses the same system parameter as the board and the systray."""
        test_record = self.test_model.create({"test_field": 1.0})
        reviews = test_record.request_validation()
        reviews._update_review_status()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE tier_review SET create_date = now() - interval '10 days' "
            "WHERE id IN %s",
            [tuple(reviews.ids)],
        )
        reviews.invalidate_recordset(["create_date"])
        digest = self._build_digest().with_user(self.test_user_1)
        param = self.env["ir.config_parameter"].sudo()
        param.set_param("base_tier_validation.late_after_days", "7")
        self.assertEqual(digest.kpi_tier_validation_late_value, 1)
        param.set_param("base_tier_validation.late_after_days", "30")
        digest.invalidate_recordset(["kpi_tier_validation_late_value"])
        self.assertEqual(digest.kpi_tier_validation_late_value, 0)

    def test_tips_render_with_working_links(self):
        """Tips are emailed, so their links must be absolute and lead to an
        existing action."""
        tips = (
            self.env["digest.tip"]
            .search([("name", "ilike", "Tip:")])
            .filtered(
                lambda t: t.get_external_id()[t.id].startswith(
                    "tier_validation_digest."
                )
            )
        )
        self.assertGreaterEqual(len(tips), 6)
        base_url = tips[:1].get_base_url()
        render = self.env["mail.render.mixin"].sudo()._render_template
        for tip in tips:
            html = render(
                tip.tip_description,
                "digest.tip",
                tip.ids,
                engine="qweb",
                options={"post_process": True},
            )[tip.id]
            self.assertIn(tip.name, html)
            for xmlid in re.findall(r'href="[^"]*/odoo/action-([\w.]+)"', html):
                self.assertTrue(self.env.ref(xmlid, raise_if_not_found=False), xmlid)
            for href in re.findall(r'href="([^"]*)"', html):
                self.assertTrue(href.startswith(base_url), href)
            images = re.findall(r'<img[^>]* src="([^"]*)"', html)
            self.assertTrue(images, f"{tip.name} has no image")
            for src in images:
                self.assertTrue(src.startswith(base_url), src)
                self.assertTrue(file_path(src[len(base_url) :].lstrip("/")), src)
