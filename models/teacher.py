from odoo import models, fields, api, _


class Teacher(models.Model):
    _name = 'silina.teacher'
    _description = 'Enseignant'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Lien avec HR Employee
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True,
        ondelete='cascade',
        tracking=True
    )

    name = fields.Char(
        related='employee_id.name',
        string='Nom',
        store=True,
        readonly=True
    )

    image_1920 = fields.Image(
        related='employee_id.image_1920',
        string='Photo'
    )

    # Informations de base
    teacher_code = fields.Char(
        string='Code enseignant',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True
    )

    # Informations de contact
    email = fields.Char(
        related='employee_id.work_email',
        string='Email',
        store=True
    )
    phone = fields.Char(
        related='employee_id.work_phone',
        string='Téléphone',
        store=True
    )
    mobile = fields.Char(
        related='employee_id.mobile_phone',
        string='Mobile',
        store=True
    )

    # Informations professionnelles
    department_id = fields.Many2one(
        related='employee_id.department_id',
        string='Département',
        store=True
    )

    job_id = fields.Many2one(
        related='employee_id.job_id',
        string='Poste',
        store=True
    )

    # Spécialisation
    specialization = fields.Selection([
        ('primary', 'Enseignement Primaire'),
        ('middle', 'Enseignement Collège'),
        ('high', 'Enseignement Lycée'),
        ('all', 'Tous niveaux'),
    ], string='Spécialisation', required=True, tracking=True)

    subject_ids = fields.Many2many(
        'silina.subject',
        'teacher_subject_rel',
        'teacher_id',
        'subject_id',
        string='Matières enseignées'
    )

    # Affectations
    subject_assignment_ids = fields.One2many(
        'silina.subject.assignment',
        'teacher_id',
        string='Affectations de classes'
    )

    main_classroom_ids = fields.One2many(
        'silina.classroom',
        'main_teacher_id',
        string='Classes principales'
    )

    # Qualifications
    qualification = fields.Selection([
        ('bac', 'Baccalauréat'),
        ('license', 'Licence'),
        ('master', 'Master'),
        ('phd', 'Doctorat'),
        ('other', 'Autre'),
    ], string='Qualification', tracking=True)

    experience_years = fields.Integer(
        string='Années d\'expérience',
        default=0
    )

    # Disponibilité
    date_start = fields.Date(
        string='Date de début',
        default=fields.Date.today,
        tracking=True
    )
    date_end = fields.Date(
        string='Date de fin',
        tracking=True
    )

    state = fields.Selection([
        ('active', 'Actif'),
        ('on_leave', 'En congé'),
        ('inactive', 'Inactif'),
    ], string='État', default='active', required=True, tracking=True)

    # Compteurs
    classroom_count = fields.Integer(
        string='Nombre de classes',
        compute='_compute_counts'
    )
    subject_count = fields.Integer(
        string='Nombre de matières',
        compute='_compute_counts'
    )

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('teacher_code_unique', 'unique(teacher_code)',
         'Le code enseignant doit être unique!'),
        ('employee_unique', 'unique(employee_id)',
         'Un employé ne peut être qu\'un seul enseignant!'),
    ]

    @api.depends('subject_assignment_ids')
    def _compute_counts(self):
        for record in self:
            record.classroom_count = len(record.subject_assignment_ids.mapped('classroom_id'))
            record.subject_count = len(record.subject_assignment_ids.mapped('subject_id'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('teacher_code', _('Nouveau')) == _('Nouveau'):
                vals['teacher_code'] = self.env['ir.sequence'].next_by_code(
                    'silina.teacher'
                ) or _('Nouveau')
        return super().create(vals_list)

    def action_view_classrooms(self):
        self.ensure_one()
        classrooms = self.subject_assignment_ids.mapped('classroom_id')
        return {
            'name': _('Classes'),
            'type': 'ir.actions.act_window',
            'res_model': 'silina.classroom',
            'view_mode': 'list,form',
            'domain': [('id', 'in', classrooms.ids)],
        }

    def action_view_assignments(self):
        self.ensure_one()
        return {
            'name': _('Affectations'),
            'type': 'ir.actions.act_window',
            'res_model': 'silina.subject.assignment',
            'view_mode': 'list,form',
            'domain': [('teacher_id', '=', self.id)],
            'context': {'default_teacher_id': self.id}
        }
