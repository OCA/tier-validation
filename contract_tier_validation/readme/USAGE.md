Define the tiers under *Settings > Technical > Tier Validations > Tier
Definitions*, on the *Contract* model.

A draft contract then shows the review bar. Once every tier has accepted it,
*Activate* becomes available and the contract starts invoicing.

## What is frozen after validation

Contract lines cannot be added, removed or edited once the contract has been
validated. Two groups of fields stay writable:

- `last_date_invoiced` and `recurring_next_date`, written by the invoicing
  run. Nobody approved a date, and blocking them would stop billing.
- the renewal fields from `contract_line_successor`, when it is installed
  (`date_end`, `is_auto_renew`, `is_canceled`, the successor links).
  Stopping, cancelling or renewing a line is something you do *because* a
  contract is live and approved.

To change the terms, put the contract back to draft, which re-opens the
review.

The lock is per company, under *Invoicing > Settings > Contract > Lock
contract lines after validation*. An organisation that amends running
contracts through `contract.modification` rather than re-approving them will
want it off. It is on by default.

## Fields the system writes on the contract

`base_tier_validation` blocks writes while a record is under review. A few
fields are excepted because the system, not the user, writes them:
`recurring_next_date`, `date_end`, `invoice_count` and `modification_ids`.
Add more by overriding `_get_validation_exceptions`, or per installation with
a *Tier Validation Exception*.

Note that creating any Tier Validation Exception turns on the after-validation
check for **every** field of the model, so whatever the system writes has to
be excepted too once you start using them.

Terminating a validated contract with `contract_termination` keeps working
then too: its fields (`is_terminated`, the reason, comment and date) are
excepted after validation, when that module is installed.
