# Copyright 2026 bosd
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.exceptions import ValidationError


class ContractLine(models.Model):
    _inherit = "contract.line"

    def _get_line_lock_exceptions(self):
        """Fields still writable on a line whose contract is locked.

        Two groups. The first is written by the machine: the invoicing run
        records where it got to, and nobody agreed to a date when they
        approved the contract. The second belongs to
        `contract_line_successor`: stopping, cancelling or renewing a line is
        something you do *because* a contract is live and approved, so
        freezing it would be wrong.

        Those field names are listed without depending on that module. If it
        is not installed the names are simply dropped, which keeps this a
        three-line concession instead of a whole glue addon.
        """
        names = [
            # written by the invoicing run
            "last_date_invoiced",
            "recurring_next_date",
            # lifecycle actions from contract_line_successor, when installed
            "date_end",
            "is_auto_renew",
            "manual_renew_needed",
            "is_canceled",
            "successor_contract_line_id",
            "predecessor_contract_line_id",
        ]
        line_fields = self._fields
        return [name for name in names if name in line_fields]

    def _filter_locked_by_validation(self):
        """Return the lines whose contract has been validated and is locked."""
        return self.filtered(lambda line: line.contract_id._is_locked_by_validation())

    def _check_locked_by_validation(self, vals=None):
        locked = self._filter_locked_by_validation()
        if not locked:
            return
        if vals is not None:
            forbidden = sorted(set(vals) - set(self._get_line_lock_exceptions()))
            if not forbidden:
                return
            raise ValidationError(
                self.env._(
                    "The lines of a validated contract cannot be changed.\n"
                    "Fields refused: %(fields)s\n\n"
                    "Set the contract back to draft to change its terms, or "
                    "turn off 'Lock contract lines after validation' in the "
                    "contract settings.",
                    fields=", ".join(forbidden),
                )
            )
        raise ValidationError(
            self.env._(
                "Lines cannot be added to or removed from a validated "
                "contract.\n\n"
                "Set the contract back to draft to change its terms, or turn "
                "off 'Lock contract lines after validation' in the contract "
                "settings."
            )
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("skip_validation_check"):
            records._check_locked_by_validation()
        return records

    def write(self, vals):
        if not self.env.context.get("skip_validation_check"):
            self._check_locked_by_validation(vals)
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get("skip_validation_check"):
            self._check_locked_by_validation()
        return super().unlink()
