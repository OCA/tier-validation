# Copyright 2025 360ERP (<https://www.360erp.com>)
# Copyright 2026 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "Base Tier Validation Delegation",
    "summary": "Allows users to delegate tier validation tasks when out of office.",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "website": "https://github.com/OCA/server-ux",
    "author": "360 ERP, Odoo Community Association (OCA)",
    "contributor": "Scalizer",
    "license": "AGPL-3",
    "depends": ["base_tier_validation", "base_tier_validation_formula"],
    "data": [
        "security/delegation_security.xml",
        "data/cron.xml",
        "views/res_users_views.xml",
        "views/tier_review_views.xml",
    ],
    "installable": True,
}
