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
        this.busService = useService("bus_service");
        this.dropdown = useDropdownState();
        this.fetchSystrayReviewer();
        // Keep the badge live and correct: re-fetch the authoritative count
        // whenever a tier review changes server-side, instead of nudging a
        // running +/- delta. The absolute value is a len() and so can never go
        // negative, which a delta could when an update reaches a user for whom
        // the review was never part of their pending count.
        this.busService.subscribe("base.tier.validation/updated", () =>
            this.fetchSystrayReviewer()
        );
        this.busService.start();
    }

    async fetchSystrayReviewer() {
        const groups = await this.orm.call("res.users", "review_user_count");
        let total = 0;
        for (const group of groups) {
            total += group.pending_count || 0;
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

    openReviewGroup(group) {
        this.dropdown.close();
        const context = {};
        const domain = [["can_review", "=", true]];
        if (group.active_field) {
            domain.push(["active", "in", [true, false]]);
        }
        const views = this.availableViews();

        this.action.doAction(
            {
                context,
                domain,
                name: group.name,
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
