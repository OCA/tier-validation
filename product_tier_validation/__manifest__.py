# Copyright 2025 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    "name": "Product Tier Validation",
    "summary": "Support a tier validation process for Products",
    "version": "19.0.1.0.0",
    "website": "https://github.com/ScalizerOrg/scalizer_tier-validation",
    "category": "Product",
    "author": "Scalizer, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["product", "base_tier_validation", "product_state"],
    "data": [
        "data/tier_definition.xml",
        "views/product_template_view.xml",
    ],
    "maintainers": ["Scalizer"],
}