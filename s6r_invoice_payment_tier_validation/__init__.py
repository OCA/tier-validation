# Copyright 2026 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from . import models


def _post_init_hook(env):
    """
        recompute the Payment Review State and Payment Locked
        fields for all posted vendor bills/refunds
    """
    bill_ids = env['account.move'].sudo().search(
        [('move_type', 'in', ('in_invoice', 'in_refund')),
         ('state', '=', 'posted'),

         ])
    for bill in bill_ids:
        bill.with_context(
            skip_validation_check=True,
            skip_payment_review_manual_check=True).sudo()._compute_invoice_payment_review_state()
        bill.with_context(
            skip_validation_check=True,
            skip_payment_review_manual_check=True).sudo()._compute_payment_locked()
