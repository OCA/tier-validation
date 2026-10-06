Bridge between ``account_move_tier_validation`` and
``stock_landed_costs``.

Adds the line-level fields that drive the *Create Landed Costs*
button on a vendor bill (``invoice_line_ids``, ``line_ids``,
``landed_costs_ids``) to the tier-validation exception list, so
that:

- The user can still flag a move line as ``is_landed_costs_line``
  after the bill has been validated, which is the trigger for the
  *Create Landed Costs* button to appear.
- The line-level write does not get blocked by the post-validation
  write guard.

Use case: a draft bill is tier-validated by purchasing; stock
operations then mark one of the lines as a landed cost (e.g.
"transport" or "duty") and click *Create Landed Costs* to push the
amount into stock valuation. Without this bridge, the line is
locked at the moment validation lands and the user cannot reach
the button.

The module auto-installs when both ``account_move_tier_validation``
and ``stock_landed_costs`` are present.
