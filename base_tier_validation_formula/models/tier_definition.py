# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import test_python_expr


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    python_code = fields.Text(
        string="Tier Definition Expression",
        help="Write Python code that defines when this tier confirmation "
        "will be needed. The result of executing the expresion must be "
        "a boolean.",
        default="""# Available locals:\n#  - rec: current record\nTrue""",
    )
    definition_type = fields.Selection(
        selection_add=[("formula", "Formula"), ("domain_formula", "Domain & Formula")]
    )
    reviewer_expression = fields.Text(
        string="Review Expression",
        help="Write Python code that defines the reviewer. "
        "The result of executing the expression must be a res.users "
        "recordset.",
        default="# Available locals:\n#  - rec: current record\n"
        "#  - Expects a recordset of res.users\nrec.env.user",
    )
    review_type = fields.Selection(selection_add=[("expression", "Python Expression")])

    @api.constrains(
        "definition_type", "python_code", "review_type", "reviewer_expression"
    )
    def _check_python_expressions(self):
        """Refuse expressions that cannot run, on save.

        Otherwise a typo only shows when someone requests a validation, on
        their document. Like server actions, this catches syntax errors and
        forbidden code; a wrong field name still shows at evaluation.
        """
        for tier in self:
            to_check = []
            if tier.definition_type in ("formula", "domain_formula"):
                to_check.append(
                    (tier.python_code, self.env._("Tier Definition Expression"))
                )
            if tier.review_type == "expression":
                to_check.append(
                    (tier.reviewer_expression, self.env._("Review Expression"))
                )
            for expression, label in to_check:
                msg = test_python_expr(expr=(expression or "").strip(), mode="eval")
                if msg:
                    raise ValidationError(
                        self.env._(
                            "%(label)s of %(tier)s is not valid:\n%(error)s",
                            label=label,
                            tier=tier.display_name,
                            error=msg,
                        )
                    )

    @api.onchange("review_type")
    def onchange_review_type(self):
        res = super().onchange_review_type()
        self.reviewer_expression = (
            "# Available locals:\n"
            "#  - rec: current record\n"
            "#  - Expects a recordset of res.users\n"
            "rec.env.user"
        )
        return res
