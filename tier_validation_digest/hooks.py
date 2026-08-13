# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def _post_init_hook(env):
    """Enable the "pending for you" tile on every existing digest record.

    Newly-created digests already get the same default via the field
    declaration (``default=True`` on
    ``kpi_tier_validation_pending``). The hook closes the loop for
    digests that existed before this module was installed -- so users
    who already have a configured digest start seeing the count
    on their next periodic email without having to revisit the
    configuration screen.

    The other three KPIs (waiting, validated-this-period, team-pending)
    stay opt-in. The pending-count is the only one that maps to an
    immediate "you have homework" signal; the rest are
    nice-to-have / managerial views and should not be turned on for
    everyone by default.
    """
    env["digest.digest"].search([]).write(
        {"kpi_tier_validation_pending": True},
    )
