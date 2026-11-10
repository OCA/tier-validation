# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    _copy_reviewer_to_reviewer_ids(cr)
    # 20.0 renders activity icons with Material Symbols; the record is noupdate.
    cr.execute(
        """
        UPDATE mail_activity_type mat
        SET icon = 'notifications'
        FROM ir_model_data imd
        WHERE imd.module = 'base_tier_validation'
            AND imd.name = 'mail_act_tier_validation_reminder'
            AND imd.model = 'mail.activity.type'
            AND imd.res_id = mat.id
            AND mat.icon = 'fa-bell'
        """
    )


def _copy_reviewer_to_reviewer_ids(cr):
    # reviewer_id (one user) becomes the multi-user reviewer_ids relation.
    cr.execute(
        """
        INSERT INTO tier_definition_res_users_rel
            (tier_definition_id, res_users_id)
        SELECT id, reviewer_id FROM tier_definition
        WHERE reviewer_id IS NOT NULL
        """
    )
