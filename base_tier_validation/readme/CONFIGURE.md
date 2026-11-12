## Tier definitions

Go to *Settings \> Technical \> Tier Validations \> Tier Definition* and create one definition per approval step. On a definition:

- **Referenced Model** is the type of document, for example *Purchase Order*. Only models that have a tier validation module installed are listed.
- **Domain** (*Apply On*) chooses which documents need this review, for example the purchase orders with an untaxed amount above 5,000. Leave it empty to review every document of that model.
- **Validated by** says who reviews:
  - *Specific user*: one user.
  - *Any user in a specific group*: one member of the group is enough. Tick **Four-eyes Principle** to stop the user who asked for the validation from approving their own request.
  - *Field in related record*: a user or group field of the document, for example its salesperson.
- **Company**: the definition only applies to documents of that company. Leave it empty to apply it to all companies.

A document gets one review for every definition whose domain matches. All of them have to be approved; one rejection rejects the document.

### Order of the reviews

The reviews of a document are ordered by the **Sequence** of their definitions, **highest first**. Beware: in the list of definitions you can drag them, and dragging a definition to the top gives it the *lowest* sequence, so it becomes the *last* tier.

By default the order is only informative: all reviewers can approve at the same time, in any order. Tick **Approve by sequence** to make a tier wait until the tiers before it are approved; its reviewers are only asked to act (and notified, see below) when it is their turn. With **Approve Sequence Bypass**, a tier is approved automatically when the same user has just approved the tier before it.

### Reviewing

- **Allow Write For Reviewers**: reviewers can edit the document while it is under validation (see the exceptions below). This applies only when every definition of the document allows it.
- **Comment**: reviewers are asked for a comment when they approve or reject. **Approve Comment** prefills the comment on approval.

### Notifications

Reviewers can be notified by email when a review is created for them, when it is their turn (*reaching Pending*, useful with *Approve by sequence*), and when a review is approved, rejected or restarted. **Send reminder message on pending reviews** posts a reminder on the document every so many days, until the review is done (0 means no reminder).

## Tier validation exceptions

From the moment a validation is requested until the document reaches its validated state (for example *Purchase Order*), the document is locked: only its followers and its access token can change. That is the point of the review: what was approved is what goes through. Reviewers can still edit it if their definitions *Allow Write For Reviewers*.

A *tier validation exception* lists the fields that stay editable. Go to *Settings \> Technical \> Tier Validations \> Tier Validation Exceptions*, choose the model and the fields, and when they may be changed:

- **Write under Validation**: while the document waits for its reviews, for example an internal note.
- **Write after Validation**: once the document is validated. As soon as a model has an exception, its validated documents are locked too, except for the fields of exceptions with this option.

With **Groups**, the exception only applies to the members of those groups. With **Company**, only to the documents of that company.
