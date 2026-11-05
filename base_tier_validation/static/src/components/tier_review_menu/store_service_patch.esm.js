import {Store} from "@mail/core/common/store_service";
import {patch} from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        // Declared here so they become reactive store fields.
        this.tierReviewCounter = 0;
        this.tierReviewGroups = [];
    },
});
