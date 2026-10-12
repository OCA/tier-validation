# Copyright 2026 bosd
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    contract_lock_lines_after_validation = fields.Boolean(
        string="Lock contract lines after validation",
        default=True,
        help="Once a contract has passed its validation, stop its lines from "
        "being added, removed or edited, so the terms that were approved are "
        "the terms that run. The invoicing run and the renewal actions keep "
        "working. Turn this off for companies that amend running contracts "
        "instead of re-approving them.",
    )
