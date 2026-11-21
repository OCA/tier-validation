Adds Tier Validation counts to the periodic KPI **Digest** email, so recipients see at a glance:

- how many tier reviews are **pending** their action right now;
- how many are **queued** behind another tier (with *Approve by sequence*), so you see what is coming;
- how many of their open reviews are **late**, using the same threshold as the review board and the systray;
- how many reviews **they validated** during the digest period;
- for managers, how many reviews are pending across the company.

Each tile's *Open Report* link opens the matching list of the review board of `base_tier_validation_board`: your pending, queued or late reviews, the reviews you validated, or all pending reviews for the team tile.

Installs automatically when `base_tier_validation_board` and `digest` are both installed.
