# Copyright 2026 bosd
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Contract Tier Validation",
    "summary": "Extends contracts to support a tier validation process",
    "version": "19.0.1.0.0",
    "category": "Contract Management",
    "license": "AGPL-3",
    "author": "bosd, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/tier-validation",
    "maintainers": ["bosd"],
    "depends": ["contract_state", "base_tier_validation"],
    "data": [
        "data/mail_data.xml",
        "views/contract_view.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
}
