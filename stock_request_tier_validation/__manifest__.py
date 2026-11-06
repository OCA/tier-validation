# Copyright 2026 Jarsa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Stock Request Tier Validation",
    "summary": "Extends the functionality of Stock Requests to "
    "support a tier validation process.",
    "version": "19.0.1.0.0",
    "category": "Warehouse Management",
    "website": "https://github.com/OCA/tier-validation",
    "author": "Jarsa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": ["stock_request", "base_tier_validation"],
    "data": [
        "views/stock_request_views.xml",
        "views/stock_request_order_views.xml",
    ],
    "installable": True,
}
