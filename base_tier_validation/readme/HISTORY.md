## 19.0.1.1.0 (2026-05-13)

UI improvements:

- Tier Definition search view: add an explicit *Archived* filter so
  archived definitions can be surfaced in one click. The existing
  *All* filter is preserved.
- Tier Definition form view: render ``reviewer_id`` (individual
  review type) with the ``many2one_avatar_user`` widget so the
  reviewer's avatar is shown next to the name, matching the rest of
  Odoo.
- Tier Definition list view: same ``many2one_avatar_user`` widget on
  ``reviewer_id``.
- Tier Definition *More Options* tab renamed to *Notifications &
  Options* and split into two clearly-titled columns: *Notify
  reviewers when* (all ``notify_*`` flags + ``notify_reminder_delay``)
  and *Review options* (``has_comment``). The previous flat group
  mixed conceptually different settings.
- Tier Review list view: render ``requested_by`` and ``done_by`` with
  ``many2one_avatar_user``. Add ``decoration-warning`` for pending
  rows and ``decoration-muted`` for waiting rows so the row state is
  visible at a glance, matching the existing decorations for rejected
  and approved.
- Tier Definition action: add a helpful empty-state message
  explaining what tier definitions are and how to chain them.

## 19.0.1.0.1 (2026-05-12)

Fixes:

- Restore auto-promotion of the lowest-sequence review to ``pending``
  immediately after ``request_validation`` so the workflow can move
  forward without an external trigger. The 19.0 migration had moved
  this side-effect out of ``_compute_can_review`` into a separate
  ``_update_review_status`` that was only invoked when the requester
  was themself the first reviewer or when ``notify_on_create`` was
  set, leaving reviews stuck in ``waiting`` in every other case.
- Coerce ``next_review`` to ``False`` when no review is pending, so
  the "needs to be validated" banner no longer leaks the empty
  ``tier.review()`` recordset repr into its ``Char`` field.
- Fix ``_notify_review_available`` so the reviewer reached by
  ``notify_on_pending`` is actually delivered the message. The
  tier-validation subtypes have ``default=False`` so a plain
  ``message_subscribe(partner_ids=...)`` left the reviewer subscribed
  only to default subtypes; ``message_post`` with the
  ``mt_tier_validation_requested`` subtype then routed to nobody. Pass
  ``subtype_ids`` explicitly (mirroring ``_notify_review_requested``).

## 17.0.1.0.0 (2024-01-10)

Migrated to Odoo 17.
Merged module with tier_validation_waiting.
To support sending messages in a validation sequence when it is their turn to validate.

## 14.0.1.0.0 (2020-11-19)

Migrated to Odoo 14.

## 13.0.1.2.2 (2020-08-30)

Fixes:

- When using approve_sequence option in any tier.definition there can be
  inconsistencies in the systray notifications
- When using approve_sequence, still not approve only the needed
  sequence, but also other sequence for the same approver

## 12.0.3.3.1 (2019-12-02)

Fixes:

- Show comment on Reviews Table.
- Edit notification with approve_sequence.

## 12.0.3.3.0 (2019-11-27)

New features:

- Add comment on Reviews Table.
- Approve by sequence.

## 12.0.3.2.1 (2019-11-26)

Fixes:

- Remove message_subscribe_users

## 12.0.3.2.0 (2019-11-25)

New features:

- Notify reviewers

## 12.0.3.1.0 (2019-07-08)

Fixes:

- Singleton error

## 12.0.3.0.0 (2019-12-02)

Fixes:

- Edit Reviews Table

## 12.0.2.1.0 (2019-05-29)

Fixes:

- Edit drop-down style width and position

## 12.0.2.0.0 (2019-05-28)

New features:

- Pass parameters as functions.
- Add Systray.

## 12.0.1.0.0 (2019-02-18)

Migrated to Odoo 12.

## 11.0.1.0.0 (2018-05-09)

Migrated to Odoo 11.

## 10.0.1.0.0 (2018-03-26)

Migrated to Odoo 10.

## 9.0.1.0.0 (2017-12-02)

First version.
