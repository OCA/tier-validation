As an end user, open *Settings > Technical > Email > Digest Emails* and
edit your digest preference. The new **Tier Validation** group exposes
four toggles:

- *Tier reviews pending for you* -- count of reviews you are allowed to
  act on right now.
- *Tier reviews queued for you* -- count of reviews waiting behind a
  lower-sequence tier you are not yet allowed to act on.
- *Tier reviews you validated this period* -- count of reviews you
  approved during the digest period.
- *Tier reviews pending across team* -- total pending across every
  reviewer in the company. Only visible to users with the
  *Administration / Settings* access right.

Pick the tiles you want to receive; the digest cron will include them
in your next periodic email. Each tile in the email links to the
matching ``tier.review`` list, pre-filtered.

The *Tier reviews pending for you* tile is enabled out of the box on
every existing digest at install time and on every digest created
afterwards. The other three tiles are opt-in -- toggle them on if you
want them.

You can also reach the same lists directly from the *Tier Validations*
menu via the *Tier Definition* action (using its search-view filters).
