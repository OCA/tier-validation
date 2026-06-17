# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Account Move Tier Validation - Stock Landed Costs Bridge",
    "summary": (
        "Allow vendor bills to be turned into a Landed Cost after tier validation"
    ),
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
        "account_move_tier_validation",
        "stock_landed_costs",
    ],
}
