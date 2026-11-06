# Copyright 2025 360ERP
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Move Tier Validation Approver Group",
    "summary": "Allow a group of users to be responsible for approving vendor bills",
    "version": "20.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "360 ERP,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/tier-validation",
    "depends": [
        "account_move_tier_validation_approver",
    ],
    "data": [
        "views/account_move.xml",
        "views/res_partner.xml",
        "views/res_config_settings_views.xml",
    ],
    "pre_init_hook": "pre_init_hook",
}
