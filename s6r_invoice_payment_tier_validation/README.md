Scalizer Invoice Payment Tier Validation
==================================
This module introduces a payment approval workflow for vendor bills based on the OCA
base_tier_validation framework.

It ensures that vendor bills must be approved for payment before any payment can be
registered, unless they are explicitly excluded (e.g. intragroup invoices).

The module adds a dedicated Payment Review State on vendor bills and controls whether
payment is allowed depending on the review outcome.

## What This Module Does

- Adds a **Payment Review State** on vendor bills
- Blocks payment if the bill is not approved
- Integrates with tier validation workflow
- Allows optional manual override for authorized users

## How It Works

1. A vendor bill is posted.
2. If approval is required, the bill goes to **To Review**.
3. Reviewers approve or reject it.
4. Only bills marked **Approved** can be paid.
5. If rejected, payment is blocked.

## Manual Override (Optional)

A special security group allows certain users to manually change the
payment review state when necessary: "Payment Review Manual State Override"

## Authors

* Scalizer

## Contributors

* Houda BENTALEB

## Maintainers

This module is maintained by [Scalizer](https://www.scalizer.fr).

![Scalizer](./static/description/logo.png)
