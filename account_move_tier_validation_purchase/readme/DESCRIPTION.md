Bridge between ``account_move_tier_validation`` and ``purchase``.

Adds the Purchase-Order auto-complete fields on a vendor bill
(``purchase_vendor_bill_id``, ``purchase_id``, ``invoice_vendor_bill_id``,
``invoice_origin``, ``invoice_line_ids``, ``line_ids``) to the
tier-validation exception list, so that:

- The fields stay editable in the form view after a bill reaches
  ``validation_status='validated'``.
- The onchange-driven write that the Auto-complete picker fires is not
  blocked by the post-validation write guard.

Use case: a purchasing user requests and obtains validation on a
draft bill; a finance user then attaches the matching PO using the
*Auto-complete from a past purchase order* picker. Without this
bridge, the picker is greyed out the moment validation lands.

The module auto-installs when both ``account_move_tier_validation``
and ``purchase`` are present.
