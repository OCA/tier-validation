This is the list of known issues for this module. Any proposal for
improvement will be very valuable.

- **Issue:**

  When using approve_sequence option in any tier.definition there can be
  inconsistencies in the systray notifications.

  **Description:**

  Field can_review in tier.review is used to filter out, in the systray
  notifications, the reviews a user can approve. This can_review field
  is updated **in the database** in method review_user_count, this can
  make it very inconsistent for databases with a lot of users and
  recurring updates that can change the expected behavior.

- **Issue:**

  A higher sequence makes an earlier tier.

  **Description:**

  Everywhere else in Odoo a lower sequence comes first, and the tier
  definition list has a drag handle: dragging a definition to the top
  gives it the lowest sequence, which makes it the last tier. Many users
  find this confusing. For 20.0, order tiers by ascending sequence, with
  a migration that inverts the sequences of existing definitions so that
  their chains keep their order.
