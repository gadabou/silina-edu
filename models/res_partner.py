from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_student = fields.Boolean(string='Est un étudiant')
    is_parent = fields.Boolean(string='Est un parent')
    is_teacher = fields.Boolean(string='Est un enseignant')

    silina_student_id = fields.Many2one(
        'silina.student',
        string='Étudiant lié',
        help="Étudiant lié à ce contact"
    )

    silina_parent_id = fields.Many2one(
        'silina.parent',
        string='Parent lié',
        help="Parent lié à ce contact"
    )

    silina_teacher_id = fields.Many2one(
        'silina.teacher',
        string='Enseignant lié',
        help="Enseignant lié à ce contact"
    )
