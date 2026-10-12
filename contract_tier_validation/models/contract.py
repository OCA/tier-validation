# Copyright 2026 bosd
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ContractContract(models.Model):
    _name = "contract.contract"
    _inherit = ["contract.contract", "tier.validation"]
    _state_from = ["draft"]
    _state_to = ["active"]

    _tier_validation_manual_config = False

    # contract_state creates contracts active so that installing it on its own
    # never stops anybody's invoicing. Here a contract is not agreed until its
    # reviews have passed, so it starts in draft instead.
    state = fields.Selection(default="draft")

    def _get_system_written_fields(self):
        """Fields written by the machine rather than agreed by a reviewer.

        Nobody approves the date an invoice was raised or the text of a cron
        failure, so these must stay writable whichever gate is in force.

        Names that only exist once another module is installed are dropped,
        so the list can mention them without depending on it.
        """
        names = [
            # recomputed from the lines or recorded by the invoicing run
            "recurring_next_date",
            "date_end",
            "last_date_invoiced",
            # the recurring-invoice cron's error reporting
            "invoice_generation_error",
            "invoice_generation_error_date",
            # counters and bookkeeping
            "invoice_count",
            "modification_ids",
        ]
        return [name for name in names if name in self._fields]

    def _get_lifecycle_fields(self):
        """Fields written by ending a contract that runs.

        Terminating a contract (``contract_termination``) is something you do
        *because* it is live and approved, like the renewal actions the line
        lock lets through. Those names are dropped when the module is not
        installed.
        """
        names = [
            "is_terminated",
            "terminate_reason_id",
            "terminate_comment",
            "terminate_date",
        ]
        return [name for name in names if name in self._fields]

    def _get_under_validation_exceptions(self):
        """Fields the system may write while a contract is under review.

        Deliberately hooked here rather than on `_get_validation_exceptions`.
        That one also decides whether the *after* validation gate is armed at
        all, so extending it would silently freeze every field of every
        validated contract - including the dates the invoicing run has to
        write. This is the same trap that makes account_move_tier_validation
        carry such a long exception list.
        """
        return super()._get_under_validation_exceptions() + (
            self._get_system_written_fields()
        )

    def _get_after_validation_exceptions(self):
        """The same fields, for when an administrator arms the second gate.

        Adding any Tier Validation Exception - to freeze the template, say -
        switches the after-validation check on for every field. Without this
        the recurring-invoice cron could no longer record that a contract
        failed to invoice, which would break the error reporting at exactly
        the moment it is needed. Listing them here allows them without
        arming anything, because the arming condition reads
        `_get_validation_exceptions` and this does not feed it.
        """
        return (
            super()._get_after_validation_exceptions()
            + self._get_system_written_fields()
            + self._get_lifecycle_fields()
        )

    def _validate_tier(self, tiers=False):
        """Activate the contract as soon as the last review is accepted.

        The sibling modules leave the record for the user to confirm, because
        there confirming does real work: a sale order reserves stock, a move
        posts entries. Activating a contract does none of that. It sets the
        field the reviewers have just agreed to, so asking for a second click
        only adds a step that can have one outcome.

        The Activate button stays for contracts that match no tier definition
        and so are never reviewed.
        """
        res = super()._validate_tier(tiers=tiers)
        self._activate_if_validated()
        return res

    def _activate_if_validated(self):
        for record in self:
            if record.state not in self._state_from:
                continue
            # The reviews were just written, so everything read from them is
            # stale. Drop the whole record rather than validation_status
            # alone: need_validation is computed from review_ids too, and a
            # cached empty review set makes base_tier_validation treat the
            # activation below as a fresh request and call back into
            # _validate_tier, which recurses until the stack runs out.
            record.invalidate_recordset()
            if record.validation_status == "validated":
                # The reviewer approves; they do not necessarily have write
                # access to the contract itself. The transition is the system
                # acting on that approval, so it runs with elevated rights.
                record.sudo().action_activate()

    def _is_locked_by_validation(self):
        """Whether this contract's terms are frozen by a completed validation.

        Locked once the review passed and the contract left draft, which
        includes the cancelled state: a cancelled contract is history and
        should not be rewritten either.
        """
        self.ensure_one()
        if not self.company_id.contract_lock_lines_after_validation:
            return False
        if self.validation_status != "validated":
            return False
        return self.state in (self._state_to + [self._cancel_state])

    def _get_to_validate_message_name(self):
        return self.env._("Contract")

    def _get_requested_notification_subtype(self):
        return "contract_tier_validation.mt_contract_tier_validation_requested"

    def _get_accepted_notification_subtype(self):
        return "contract_tier_validation.mt_contract_tier_validation_accepted"

    def _get_rejected_notification_subtype(self):
        return "contract_tier_validation.mt_contract_tier_validation_rejected"
