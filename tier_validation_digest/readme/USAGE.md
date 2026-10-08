Open *Settings > Technical > Email > Digest Emails* and edit a digest. The **Tier Validation** group has five toggles:

- *Tier reviews pending for you*: reviews you can act on right now.
- *Tier reviews queued for you*: reviews waiting behind an earlier tier you are not allowed to act on yet.
- *Tier reviews late for you*: your open reviews older than the late threshold.
- *Tier reviews you validated this period*: reviews you approved during the digest period.
- *Tier reviews pending across team*: all pending reviews in the company. Only visible to users with the *Administration / Settings* access right.

*Tier reviews pending for you* is switched on for every digest, existing ones included. The others are opt-in.

The late threshold is the `base_tier_validation.late_after_days` system parameter (default 7 days), the same one the review board and the reviewer systray use.

The same lists are in *Dashboards > Tier Reviews*.
