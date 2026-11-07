1. Open the documents to review, for example from the reviews systray menu,
   and select them in the list or kanban view (or *Select all*).
2. Click *Validate* or *Reject* next to the selection. The requester uses
   *Request Validation* the same way.
3. A notification tells how many documents were processed and how many were
   skipped.

Only the reviews of definitions with *Allow Multi Validation* are validated or
rejected, and only on documents where the current user could validate them from
the form. Other documents are skipped. The reviews are processed in tier order,
up to the first tier that does not allow multi validation: that tier is
validated from the form, as are the following ones.

When a definition asks for a comment, validating uses its *Approve Comment*.
Without one, and always to reject, the comment is asked once for all the
selected documents.
