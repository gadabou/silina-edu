from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class Student(models.Model):
    _name = 'silina.student'
    _description = 'Étudiant'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Informations de base
    name = fields.Char(
        string='Nom complet',
        required=True,
        tracking=True
    )
    first_name = fields.Char(
        string='Prénom',
        required=True,
        tracking=True
    )
    last_name = fields.Char(
        string='Nom',
        required=True,
        tracking=True
    )
    registration_number = fields.Char(
        string='Numéro de matricule',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True
    )

    image_1920 = fields.Image(
        string='Photo',
        max_width=1920,
        max_height=1920
    )
    image_128 = fields.Image(
        string='Photo (128)',
        related='image_1920',
        max_width=128,
        max_height=128,
        store=True
    )

    gender = fields.Selection([
        ('male', 'Masculin'),
        ('female', 'Féminin'),
    ], string='Sexe', required=True, tracking=True)

    date_of_birth = fields.Date(
        string='Date de naissance',
        required=True,
        tracking=True
    )
    age = fields.Integer(
        string='Âge',
        compute='_compute_age',
        store=True
    )
    place_of_birth = fields.Char(
        string='Lieu de naissance',
        tracking=True
    )

    nationality = fields.Many2one(
        'res.country',
        string='Nationalité',
        tracking=True
    )

    blood_group = fields.Selection([
        ('a+', 'A+'),
        ('a-', 'A-'),
        ('b+', 'B+'),
        ('b-', 'B-'),
        ('o+', 'O+'),
        ('o-', 'O-'),
        ('ab+', 'AB+'),
        ('ab-', 'AB-'),
    ], string='Groupe sanguin')

    # Informations de contact
    email = fields.Char(string='Email')
    phone = fields.Char(string='Téléphone')
    mobile = fields.Char(string='Mobile')

    # Adresse
    street = fields.Char(string='Rue')
    street2 = fields.Char(string='Rue 2')
    city = fields.Char(string='Ville')
    state_id = fields.Many2one('res.country.state', string='État')
    zip = fields.Char(string='Code postal')
    country_id = fields.Many2one('res.country', string='Pays')

    # Informations académiques
    academic_year_id = fields.Many2one(
        'silina.academic.year',
        string='Année Scolaire',
        required=True,
        tracking=True,
        default=lambda self: self.env['silina.academic.year'].get_current_year()
    )

    classroom_id = fields.Many2one(
        'silina.classroom',
        string='Classe',
        tracking=True,
        domain="[('academic_year_id', '=', academic_year_id)]"
    )

    level_id = fields.Many2one(
        related='classroom_id.level_id',
        string='Niveau',
        store=True,
        readonly=True
    )

    degree = fields.Selection(
        related='classroom_id.degree',
        string='Degré',
        store=True,
        readonly=True
    )

    enrollment_date = fields.Date(
        string='Date d\'inscription',
        default=fields.Date.today,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('enrolled', 'Inscrit'),
        ('promoted', 'Admis'),
        ('repeated', 'Redoublant'),
        ('transferred', 'Transféré'),
        ('graduated', 'Diplômé'),
        ('expelled', 'Exclu'),
    ], string='État', default='draft', required=True, tracking=True)

    # Parents/Tuteurs
    parent_ids = fields.Many2many(
        'silina.parent',
        'student_parent_rel',
        'student_id',
        'parent_id',
        string='Parents/Tuteurs'
    )

    father_name = fields.Char(string='Nom du père')
    mother_name = fields.Char(string='Nom de la mère')
    guardian_name = fields.Char(string='Nom du tuteur')

    # Documents
    document_ids = fields.One2many(
        'silina.student.document',
        'student_id',
        string='Documents'
    )

    # Résultats d'examens
    exam_result_ids = fields.One2many(
        'silina.exam.result',
        'student_id',
        string='Résultats d\'examens'
    )

    # Frais scolaires
    fee_ids = fields.One2many(
        'silina.student.fee',
        'student_id',
        string='Frais scolaires'
    )
    fee_payment_ids = fields.One2many(
        'silina.fee.payment',
        'student_id',
        string='Paiements'
    )

    total_fees = fields.Monetary(
        string='Total des frais',
        compute='_compute_fee_totals',
        currency_field='currency_id'
    )
    total_paid = fields.Monetary(
        string='Total payé',
        compute='_compute_fee_totals',
        currency_field='currency_id'
    )
    total_due = fields.Monetary(
        string='Reste à payer',
        compute='_compute_fee_totals',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id
    )

    # Informations médicales
    allergies = fields.Text(string='Allergies')
    medical_conditions = fields.Text(string='Conditions médicales')
    emergency_contact_name = fields.Char(string='Contact d\'urgence')
    emergency_contact_phone = fields.Char(string='Téléphone d\'urgence')

    # Autres
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('registration_number_unique', 'unique(registration_number)',
         'Le numéro de matricule doit être unique!'),
    ]

    @api.depends('first_name', 'last_name')
    def _compute_name(self):
        for record in self:
            if record.first_name and record.last_name:
                record.name = f"{record.first_name} {record.last_name}"

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for record in self:
            if record.date_of_birth:
                age = today.year - record.date_of_birth.year
                if today.month < record.date_of_birth.month or \
                   (today.month == record.date_of_birth.month and today.day < record.date_of_birth.day):
                    age -= 1
                record.age = age
            else:
                record.age = 0

    @api.depends('fee_ids', 'fee_ids.amount', 'fee_payment_ids', 'fee_payment_ids.amount')
    def _compute_fee_totals(self):
        for record in self:
            record.total_fees = sum(record.fee_ids.mapped('amount'))
            record.total_paid = sum(record.fee_payment_ids.filtered(
                lambda p: p.state == 'paid'
            ).mapped('amount'))
            record.total_due = record.total_fees - record.total_paid

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('registration_number', _('Nouveau')) == _('Nouveau'):
                vals['registration_number'] = self.env['ir.sequence'].next_by_code(
                    'silina.student'
                ) or _('Nouveau')
            if vals.get('first_name') and vals.get('last_name'):
                vals['name'] = f"{vals['first_name']} {vals['last_name']}"
        return super().create(vals_list)

    def write(self, vals):
        if 'first_name' in vals or 'last_name' in vals:
            for record in self:
                first_name = vals.get('first_name', record.first_name)
                last_name = vals.get('last_name', record.last_name)
                vals['name'] = f"{first_name} {last_name}"
        return super().write(vals)

    def action_enroll(self):
        self.ensure_one()
        if not self.classroom_id:
            raise ValidationError(_('Veuillez assigner une classe à l\'étudiant avant de l\'inscrire!'))
        self.state = 'enrolled'
        return True

    def action_promote(self):
        self.ensure_one()
        self.state = 'promoted'
        return True

    def action_repeat(self):
        self.ensure_one()
        self.state = 'repeated'
        return True

    def action_view_fees(self):
        self.ensure_one()
        return {
            'name': _('Frais Scolaires'),
            'type': 'ir.actions.act_window',
            'res_model': 'silina.student.fee',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id}
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'name': _('Paiements'),
            'type': 'ir.actions.act_window',
            'res_model': 'silina.fee.payment',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id}
        }

    def action_generate_report_card(self):
        self.ensure_one()
        return {
            'name': _('Générer le bulletin de notes'),
            'type': 'ir.actions.act_window',
            'res_model': 'silina.generate.report.card.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_student_ids': [(6, 0, self.ids)]}
        }
