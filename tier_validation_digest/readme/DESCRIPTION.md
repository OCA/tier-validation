Adds Tier Validation counts to the periodic KPI **Digest** email so
recipients see, at a glance:

- How many tier reviews are **pending** their action right now.
- How many reviews are **queued** behind another tier (useful when
  ``approve_sequence`` is on -- you can see what is coming next without
  having to click through to each document).
- How many reviews **they validated this period** (a satisfying "I
  cleared X reviews this week" signal, tied to the digest's own
  periodicity).
- **Manager view only**: how many reviews are pending across every
  reviewer in the company.

Each KPI tile links to a filtered ``tier.review`` list so the recipient
can act on the items in one click.

Auto-installs whenever both ``base_tier_validation`` and ``digest`` are
present, so it is transparent.
