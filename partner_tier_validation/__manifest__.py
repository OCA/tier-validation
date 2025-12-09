# Copyright 2025 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    "name": "Partner Tier Validation",
    "summary": "Support a tier validation process for Contacts",
    "version": "19.0.1.0.0",
    "website": "https://github.com/OCA/partner-contact",
    "category": "Contact",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["contacts", "base_tier_validation", "partner_stage"],
    "data": [
        "data/tier_definition.xml",
        "views/res_partner_view.xml",
    ],
    "maintainers": ["Scalizer"],
}
