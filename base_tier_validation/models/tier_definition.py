# Copyright 2017 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from ast import literal_eval

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class TierDefinition(models.Model):
    _name = "tier.definition"
    _description = "Tier Definition"
    _order = "company_id, sequence, id"

    @api.model
    def _get_default_name(self):
        return self.env._("New Tier Validation")

    @api.model
    def _get_tier_validation_model_names(self):
        res = []
        return res

    name = fields.Char(
        string="Description",
        required=True,
        default=lambda self: self._get_default_name(),
        translate=True,
    )
    tier_summary = fields.Char(
        string="Summary",
        compute="_compute_tier_summary",
        help="Plain-language description of when this rule applies and who "
        "must validate.",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Referenced Model",
        domain=lambda self: [("model", "in", self._get_tier_validation_model_names())],
        help="The document type this validation rule applies to. Only models "
        "that opted in to tier validation are listed.",
    )
    model = fields.Char(related="model_id.model", index=True, store=True)
    review_type = fields.Selection(
        string="Validated by",
        default="individual",
        selection=[
            ("individual", "Specific user"),
            ("group", "Any user in a specific group"),
            ("field", "Field in related record"),
        ],
        help="Who is allowed to validate this tier:\n"
        "- Specific user: a named user.\n"
        "- Any user in a specific group: any member of the chosen group.\n"
        "- Field in related record: the user/group stored in a field of the "
        "document itself (e.g. its salesperson or manager).",
    )
    allow_write_for_reviewer = fields.Boolean(
        string="Allow Write For Reviewers",
        default=False,
    )
    reviewer_id = fields.Many2one(comodel_name="res.users", string="Reviewer")
    reviewer_group_id = fields.Many2one(
        comodel_name="res.groups", string="Reviewer group"
    )
    reviewer_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Reviewer field",
        domain="[('id', 'in', valid_reviewer_field_ids)]",
        help="A field of the document that points to the reviewer(s): a "
        "user field or a group field (e.g. the document's salesperson or "
        "approving manager).",
    )
    valid_reviewer_field_ids = fields.One2many(
        comodel_name="ir.model.fields",
        compute="_compute_domain_reviewer_field",
    )
    definition_type = fields.Selection(
        string="Definition", selection=[("domain", "Domain")], default="domain"
    )
    definition_domain = fields.Char(
        help="Filter deciding which records of the model this rule applies "
        "to. Leave empty to apply to every record. Example: "
        "[('amount_total', '>', 1000)] -- only documents whose total "
        "exceeds 1000.",
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(
        default=30,
        help="Order of this tier. Lower numbers are validated first when "
        "'Approve by sequence' is enabled.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    notify_on_create = fields.Boolean(
        string="Notify Reviewers on Creation",
        help="If set, all possible reviewers will be notified by email when "
        "this definition is triggered.",
    )
    notify_on_pending = fields.Boolean(
        string="Notify Reviewers on reaching Pending",
        help="If set, all possible reviewers will be notified by email when "
        "this status is reached."
        "Usefull in an Approve by sequence scenario. "
        "An notification request to review is sent out when it's their turn to review.",
    )
    notify_on_accepted = fields.Boolean(
        string="Notify Reviewers on Accepted",
        help="If set, reviewers will be notified by email when a review related "
        "to this definition is accepted.",
    )
    notify_on_rejected = fields.Boolean(
        string="Notify Reviewers on Rejected",
        help="If set, reviewers will be notified by email when a review related "
        "to this definition is rejected.",
    )
    notify_on_restarted = fields.Boolean(
        string="Notify Reviewers on Restarted",
        help="If set, reviewers will be notified by email when a reviews related "
        "to this definition are restarted.",
    )
    has_comment = fields.Boolean(string="Comment", default=False)
    notify_reminder_delay = fields.Integer(
        string="Send reminder message on pending reviews",
        help="Number of days after which a message must be posted to remind about "
        "pending validation  (0 = no reminder)",
    )
    approve_sequence = fields.Boolean(
        string="Approve by sequence",
        default=False,
        help="If set, this tier can only be validated once all tiers with a "
        "lower sequence number have been validated (strict order). If not "
        "set, this tier can be validated at any time.",
    )
    approve_sequence_bypass = fields.Boolean(
        help="Bypassed (auto validated), if previous tier was validated "
        "by same reviewer",
    )

    @api.onchange("review_type")
    def onchange_review_type(self):
        self.reviewer_id = None
        self.reviewer_group_id = None

    @api.depends("review_type", "model_id")
    def _compute_domain_reviewer_field(self):
        models = self.mapped("model")
        IrModelFields = self.env["ir.model.fields"].sudo()
        valid_reviewer_fields = dict(
            IrModelFields._read_group(
                domain=Domain("model", "in", models)
                & (
                    Domain("relation", "=", "res.users")
                    | Domain("relation", "=", "res.groups")
                ),
                groupby=["model"],
                aggregates=["id:array_agg"],
            )
        )
        for rec in self:
            rec.valid_reviewer_field_ids = valid_reviewer_fields.get(
                rec.model, IrModelFields
            )

    def _describe_domain(self):
        """Best-effort plain-language rendering of ``definition_domain``.

        Never raises: falls back to the raw string when the domain cannot be
        parsed or contains operators we do not spell out.
        """
        self.ensure_one()
        raw = (self.definition_domain or "").strip()
        if not raw or raw == "[]":
            return self.env._("for all records")
        try:
            parsed = literal_eval(raw)
        except (ValueError, SyntaxError):
            return self.env._("where %s", raw)
        if not isinstance(parsed, list | tuple) or not parsed:
            return self.env._("for all records")
        model = self.env[self.model] if self.model and self.model in self.env else None
        leaves = []
        for item in parsed:
            if isinstance(item, list | tuple) and len(item) == 3:
                fname, operator, value = item
                label = fname
                if model is not None and fname in model._fields:
                    label = model._fields[fname].string or fname
                leaves.append(f"{label} {operator} {value!r}")
        if not leaves:
            return self.env._("where %s", raw)
        return self.env._("where %s", " and ".join(leaves))

    def _describe_reviewer(self):
        self.ensure_one()
        by_type = {
            "individual": self.reviewer_id.display_name,
            "group": self.reviewer_group_id.display_name,
            "field": self.reviewer_field_id.field_description
            or self.reviewer_field_id.name,
        }
        return by_type.get(self.review_type) or ""

    @api.depends(
        "model_id",
        "model",
        "sequence",
        "approve_sequence",
        "review_type",
        "reviewer_id",
        "reviewer_group_id",
        "reviewer_field_id",
        "definition_domain",
    )
    def _compute_tier_summary(self):
        rt_labels = dict(self.fields_get(["review_type"])["review_type"]["selection"])
        for rec in self:
            if not rec.model_id:
                rec.tier_summary = ""
                continue
            target = rec._describe_reviewer()
            rec.tier_summary = self.env._(
                "Tier %(seq)s — %(model)s %(cond)s: validated by %(how)s"
                "%(target)s%(ordered)s",
                seq=rec.sequence,
                model=rec.model_id.name or rec.model,
                cond=rec._describe_domain(),
                how=rt_labels.get(rec.review_type, rec.review_type or ""),
                target=(" " + target) if target else "",
                ordered=self.env._(" (in sequence)") if rec.approve_sequence else "",
            )

    @api.constrains("definition_domain")
    def _check_definition_domain(self):
        for rec in self:
            raw = (rec.definition_domain or "").strip()
            if not raw:
                continue
            try:
                parsed = literal_eval(raw)
            except (ValueError, SyntaxError) as err:
                raise ValidationError(
                    self.env._(
                        "The filter of tier definition '%(name)s' is not "
                        "valid: %(err)s",
                        name=rec.name,
                        err=err,
                    )
                ) from err
            if not isinstance(parsed, list | tuple):
                raise ValidationError(
                    self.env._(
                        "The filter of tier definition '%(name)s' must be a "
                        "list of conditions, e.g. "
                        "[('amount_total', '>', 1000)].",
                        name=rec.name,
                    )
                )

    @api.onchange("definition_domain")
    def _onchange_definition_domain_warn_empty(self):
        if not (self.definition_domain or "").strip() and self.model_id:
            return {
                "warning": {
                    "title": self.env._("Heads up"),
                    "message": self.env._(
                        "This rule has no filter, so it will apply to every %s.",
                        self.model_id.name or self.model,
                    ),
                }
            }

    def _get_review_needing_reminder(self):
        """Return all the reviews that have the reminder setup."""
        self.ensure_one()
        if not self.notify_reminder_delay:
            return self.env["tier.review"]
        review_date = fields.Datetime.subtract(
            fields.Datetime.now(), days=self.notify_reminder_delay
        )
        domain = (
            Domain("definition_id", "=", self.id)
            & Domain("status", "in", ["waiting", "pending"])
            & (
                Domain("create_date", "<", review_date)
                & Domain("last_reminder_date", "=", False)
                | Domain("last_reminder_date", "<", review_date)
            )
        )
        return self.env["tier.review"].search(
            domain,
            limit=1,
        )

    def _cron_send_review_reminder(self):
        definition_with_reminder = self.env["tier.definition"].search(
            Domain("notify_reminder_delay", ">", 0)
        )
        for record in definition_with_reminder:
            review_to_remind = record._get_review_needing_reminder()
            if review_to_remind:
                review_to_remind._send_review_reminder()
