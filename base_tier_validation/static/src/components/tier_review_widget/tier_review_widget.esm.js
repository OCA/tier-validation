import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class ReviewsTable extends Component {
    _getReviewData() {
        const records = this.props.record.data.review_ids.records;
        return records.map((record) => record.data);
    }
}

ReviewsTable.template = "base_tier_validation.Collapse";

export const reviewsTableComponent = {
    component: ReviewsTable,
    supportedTypes: ["one2many"],
    relatedFields: [
        {name: "id", type: "integer"},
        {name: "sequence", type: "integer"},
        {name: "name", type: "char"},
        {name: "display_status", type: "char"},
        {name: "todo_by", type: "char"},
        {name: "status", type: "char"},
        {name: "reviewed_formated_date", type: "char"},
        {name: "comment", type: "char"},
        {name: "requested_by", type: "many2one", relation: "partner"},
        {name: "done_by", type: "many2one", relation: "partner"},
    ],
};

registry.category("fields").add("form.tier_validation", reviewsTableComponent);
