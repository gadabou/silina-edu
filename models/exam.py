from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Exam(models.Model):
    _name = 'silina.exam'
    _description = 'Examen'
    _order = 'date_start desc, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Nom',
        required=True,
        tracking=True,
        help="Ex: Examen du 1er trimestre"
    )
    code = fields.Char(
        string='Code',
        required=True,
        copy=False,
        tracking=True
    )

    exam_type = fields.Selection([
        ('monthly', 'Examen mensuel'),
        ('quarterly', 'Examen trimestriel'),
        ('semester', 'Examen semestriel'),
        ('annual', 'Examen annuel'),
        ('final', 'Examen final'),
    ], string='Type d\'examen', required=True, tracking=True)

    academic_year_id = fields.Many2one(
        'silina.academic.year',
        string='Année Scolaire',
        required=True,
        tracking=True,
        default=lambda self: self.env['silina.academic.year'].get_current_year()
    )

    date_start = fields.Date(
        string='Date de début',
        required=True,
        tracking=True
    )
    date_end = fields.Date(
        string='Date de fin',
        required=True,
        tracking=True
    )

    # Applicabilité
    level_ids = fields.Many2many(
        'silina.level',
        'exam_level_rel',
        'exam_id',
        'level_id',
        string='Niveaux concernés'
    )

    classroom_ids = fields.Many2many(
        'silina.classroom',
        'exam_classroom_rel',
        'exam_id',
        'classroom_id',
        string='Classes concernées',
        domain="[('academic_year_id', '=', academic_year_id)]"
    )

    subject_ids = fields.Many2many(
        'silina.subject',
        'exam_subject_rel',
        'exam_id',
        'subject_id',
        string='Matières'
    )

    # Résultats
    result_ids = fields.One2many(
        'silina.exam.result',
        'exam_id',
        string='Résultats'
    )
    result_count = fields.Integer(
        string='Nombre de résultats',
        compute='_compute_result_count'
    )

    # Configuration
    total_marks = fields.Float(
        string='Note maximale',
        default=20.0,
        help="Note maximale par matière"
    )
    passing_marks = fields.Float(
        string='Note de passage',
        default=10.0,
        help="Note minimale pour réussir"
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('scheduled', 'Programmé'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True)

    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_unique', 'unique(code, academic_year_id)',
         'Le code de l\'examen doit être unique pour une année scolaire!'),
    ]

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start > record.date_end:
                raise ValidationError(_('La date de fin doit être postérieure à la date de début!'))

    @api.constrains('passing_marks', 'total_marks')
    def _check_marks(self):
        for record in self:
            if record.passing_marks > record.total_marks:
                raise ValidationError(_('La note de passage ne peut pas être supérieure à la note maximale!'))

    @api.depends('result_ids')
    def _compute_result_count(self):
        for record in self:
            record.result_count = len(record.result_ids)

    def action_schedule(self):
        self.ensure_one()
        self.state = 'scheduled'
        return True

    def action_start(self):
        self.ensure_one()
        self.state = 'in_progress'
        return True

    def action_complete(self):
        self.ensure_one()
        self.state = 'completed'
        return True

    def action_view_results(self):
        self.ensure_one()
        return {
            'name': _('Résultats d\'examen'),
            'type': 'ir.actions.act_window',
            'res_model': 'silina.exam.result',
            'view_mode': 'list,form',
            'domain': [('exam_id', '=', self.id)],
            'context': {
                'default_exam_id': self.id,
                'default_total_marks': self.total_marks,
            }
        }
