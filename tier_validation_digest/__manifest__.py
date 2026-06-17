# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Tier Validation Digest",
    "summary": "Surface pending tier reviews in the KPI digest email",
    "version": "19.0.1.0.0",
    "development_status": "Beta",
    "maintainers": ["bosd"],
    "category": "Tools",
    "website": "https://github.com/OCA/tier-validation",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "auto_install": True,
    "depends": [
        "base_tier_validation",
        "digest",
    ],
    "data": [
        "views/tier_review_views.xml",
        "views/digest_views.xml",
    ],
    "post_init_hook": "_post_init_hook",
}
