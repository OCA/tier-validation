# Copyright 2026 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    "name": "Scalizer Invoice Payment Tier Validation",
    "version": "19.0.1.0.1",
    "author": "Scalizer",
    "website": "https://www.scalizer.fr",
    "category": "Accounting/Accounting",
    "summary": "Adds a payment approval workflow for vendor bills based on tier validation.",
    "description": """
The module introduces a Payment Review State on vendor bills and blocks payment
registration until the bill is approved for payment. Intragroup bills can be
excluded, and an optional security group allows authorized users to manually
override the review state when needed.
    """,
    "depends": [
        "account",
        "base_tier_validation",
        "s6r_account_invoice_intragroup"
    ],
    "data": [
        "security/security.xml",
        "data/tier_definition.xml",
        "views/account_move_views.xml",

    ],
    'post_init_hook': '_post_init_hook',

    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
