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

// Systray items render right-to-left by descending sequence (higher =
// further left; the user menu at sequence 0 is the right-most). A low
// sequence keeps the reviewer menu grouped with the standard
// notification menus (messaging 25, activities 20) on the right, rather
// than off on the far left -- notably to the right of the Enterprise AI
// button (which sits left of the messaging menu, i.e. sequence > 25).
registry
    .category("systray")
    .add("base_tier_validation.ReviewerMenu", systrayItem, {sequence: 24});
