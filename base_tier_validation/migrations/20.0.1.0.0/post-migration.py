# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def migrate(cr, version):
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
