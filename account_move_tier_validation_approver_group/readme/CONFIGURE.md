1.  Go to *Invoicing \> Configuration \> Settings*.
2.  In the *Vendor Bills* section, enable *Require Approver Group In
    Vendor Bills*. This creates (or activates) the tier definition
    "Validation with Approver field (group)". This tier only applies to
    bills that have a *Group responsible for approval*.
3.  On the vendor, in the *Sales & Purchase* tab, set the *Approver of
    Vendor Bills group*.

If you also enable *Require Approver In Vendor Bills* (the individual
approver), a bill can be posted when it has a user OR a group
responsible for approval. In this case, add a domain to the individual
tier definition ("Validation with Approver field") so that it only
applies when no group is set, for example
`[('move_type', '=', 'in_invoice'), ('approver_group_id', '=', False)]`.
