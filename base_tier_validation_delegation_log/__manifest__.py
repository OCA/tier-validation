# Copyright 2025 360ERP (<https://www.360erp.com>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "Base Tier Validation Delegation Log",
    "summary": "Provides an audit log for all delegated tier validation actions.",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "category": "Tools",
    "website": "https://github.com/OCA/server-ux",
    "author": "360 ERP, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["base_tier_validation_delegation"],
    "data": [
        "security/ir.model.access.csv",
        "security/tier_review_delegation_log_security.xml",
        "views/tier_review_delegation_log_views.xml",
    ],
}
