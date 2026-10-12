Puts contracts through a tier validation before they start running.

A contract is created in **Draft** and does not invoice. Moving it to
**Active** requires the reviews configured for `contract.contract` to pass, so
the terms are agreed internally before the first invoice is generated.

Once validated, the contract's lines are frozen: what was approved is what
runs. The invoicing run and the renewal actions carry on working.
