import {Component, useState} from "@odoo/owl";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {registry} from "@web/core/registry";
import {useDiscussSystray} from "@mail/utils/common/hooks";
import {useDropdownState} from "@web/core/dropdown/dropdown_hooks";
import {useService} from "@web/core/utils/hooks";

export class TierReviewMenu extends Component {
    static components = {Dropdown};
    static props = [];
    static template = "base_tier_validation.TierReviewMenu";

    setup() {
        super.setup();
        this.discussSystray = useDiscussSystray();
        this.orm = useService("orm");
        this.store = useState(useService("mail.store"));
        this.action = useService("action");
        this.dropdown = useDropdownState();
        this.fetchSystrayReviewer();
    }

    async fetchSystrayReviewer() {
        const groups = await this.orm.call("res.users", "review_user_count");
        let total = 0;
        for (const group of groups) {
            // Headline counter mirrors what the reviewer must act on
            // *right now*: late + pending. Future is a heads-up only
            // and shouldn't inflate the urgency badge.
            total += (group.late_count || 0) + (group.pending_count || 0);
        }
        this.store.tierReviewCounter = total;
        this.store.tierReviewGroups = groups;
    }

    availableViews() {
        return [
            [false, "kanban"],
            [false, "list"],
            [false, "form"],
            [false, "activity"],
        ];
    }

    openReviewGroup(group, bucket = "pending") {
        this.dropdown.close();
        // Per-bucket ids are pre-computed server-side so we just hand
        // them to the action's domain. Empty buckets are no-ops.
        const idsByBucket = {
            late: group.late_ids || [],
            pending: group.pending_ids || [],
            future: group.future_ids || [],
        };
        const ids = idsByBucket[bucket] || [];
        if (!ids.length) {
            return;
        }
        const labelByBucket = {
            late: "Late",
            pending: "Pending",
            future: "Future",
        };
        const domain = [["id", "in", ids]];
        if (group.active_field) {
            domain.push(["active", "in", [true, false]]);
        }
        const views = this.availableViews();

        this.action.doAction(
            {
                context: {},
                domain,
                name: `${group.name} - ${labelByBucket[bucket] || bucket}`,
                res_model: group.model,
                search_view_id: [false],
                type: "ir.actions.act_window",
                views,
            },
            {
                clearBreadcrumbs: true,
            }
        );
    }
}

export const systrayItem = {
    Component: TierReviewMenu,
};

registry
    .category("systray")
    .add("base_tier_validation.ReviewerMenu", systrayItem, {sequence: 99});
