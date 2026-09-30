# Copyright 2024 ForgeFlow S.L.  <https://www.forgeflow.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models
from odoo.tools import SQL, split_every


class TierReview(models.Model):
    _inherit = "tier.review"

    @api.depends("model", "res_id")
    def _compute_res_name(self):
        for record in self:
            if record.res_id and record.model:
                record.res_name = (
                    self.env[record.model].browse(record.res_id).display_name
                )
            else:
                record.res_name = False

    related_model_instance = fields.Reference(
        selection="_selection_related_model_instance",
        compute="_compute_related_model_instance",
        string="Document",
    )
    res_name = fields.Char(
        "Resource Name", compute="_compute_res_name", compute_sudo=True
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        related="definition_id.model_id",
        store=True,
        string="Model",
        help="Many2one to ir.model used by the pivot/graph views so the "
        "rows display the model's human-friendly description (e.g. "
        "'Journal Entry') rather than its technical name "
        "('account.move').",
    )
    response_days = fields.Float(
        string="Response (days)",
        compute="_compute_response_days",
        store=True,
        help="Days between the review being created and it being done. "
        "Empty until the review is approved or rejected. Use this as a "
        "measure in pivot/graph views to compare reviewer response time.",
    )

    @api.depends("create_date", "reviewed_date")
    def _compute_response_days(self):
        for rec in self:
            if rec.create_date and rec.reviewed_date:
                rec.response_days = (
                    rec.reviewed_date - rec.create_date
                ).total_seconds() / 86400.0
            else:
                rec.response_days = 0.0

    @api.depends("res_id", "model")
    def _compute_related_model_instance(self):
        for record in self:
            ref = False
            if record.res_id:
                ref = f"{record.model},{record.res_id}"
            record.related_model_instance = ref

    @api.model
    def _selection_related_model_instance(self):
        # Restrict the Reference selection to models that actually carry
        # tier validation. Avoids the pylint `no-search-all` warning and
        # mirrors the domain used in `tier.definition.model_id`.
        model_names = self.env["tier.definition"]._get_tier_validation_model_names()
        if not model_names:
            return []
        models = self.env["ir.model"].sudo().search([("model", "in", model_names)])
        return [(model.model, model.name) for model in models]

    def open_origin(self):
        self.ensure_one()
        vid = self.env[self.model].browse(self.res_id).get_formview_id()
        response = {
            "type": "ir.actions.act_window",
            "res_model": self.model,
            "view_mode": "form",
            "res_id": self.res_id,
            "target": "current",
            "views": [(vid, "form")],
        }
        return response

    @api.model
    def _search(self, domain, *args, **kwargs):
        # Forward arbitrary kwargs to super() (the v19 ORM keeps adding
        # them: ``bypass_access``, ``active_test``, ...). When the caller
        # has explicitly opted out of ACL or is the superuser, skip the
        # board's per-document filter -- the board filter is itself an
        # ACL, so bypass_access=True should bypass it too.
        if kwargs.get("bypass_access") or self.env.is_superuser():
            return super()._search(domain, *args, **kwargs)
        query = super()._search(domain, *args, **kwargs)
        ids = self.browse(query).ids
        if not ids:
            return query

        super().check_access("read")

        self.flush_model(["model", "res_id"])
        reviews_to_check = []
        for sub_ids in split_every(self.env.cr.IN_MAX, ids):
            self.env.cr.execute(
                SQL(
                    """
                SELECT DISTINCT review.id, review.model, review.res_id
                FROM %(table)s review
                WHERE review.id = ANY (%(ids)s) AND review.res_id != 0""",
                    table=SQL.identifier(self._table),
                    ids=list(sub_ids),
                )
            )
            reviews_to_check += self.env.cr.dictfetchall()

        review_to_documents = {}
        for review in reviews_to_check:
            review_to_documents.setdefault(review["model"], set()).add(review["res_id"])

        allowed_ids = set()
        for doc_model, doc_ids in review_to_documents.items():
            doc_operation = "read"
            DocumentModel = self.env[doc_model].with_user(self.env.uid)
            right = DocumentModel.has_access(doc_operation)
            if right:
                valid_docs = DocumentModel.browse(doc_ids)._filtered_access(
                    doc_operation
                )
                valid_doc_ids = set(valid_docs.ids)
                allowed_ids.update(
                    review["id"]
                    for review in reviews_to_check
                    if review["model"] == doc_model
                    and review["res_id"] in valid_doc_ids
                )

        id_list = [id for id in ids if id in allowed_ids]

        return super()._search([("id", "in", id_list)], *args, **kwargs)

    # NOTE: previous Odoo versions overrode ``_read_group_raw`` here to
    # re-apply the same per-document ACL the ``_search`` override above
    # enforces -- needed because the read_group path used to bypass
    # ``_search``. From Odoo 17 onwards ``_read_group_raw`` is gone and
    # ``_read_group`` routes through ``_search`` internally, so the
    # ``_search`` override already covers the read_group case and the
    # explicit override is no longer required.
