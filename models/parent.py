from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Parent(models.Model):
    _name = 'silina.parent'
    _description = 'Parent/Tuteur'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Nom complet',
        required=True,
        tracking=True
    )

    image_1920 = fields.Image(
        string='Photo',
        max_width=1920,
        max_height=1920
    )

    relation = fields.Selection([
        ('father', 'Père'),
        ('mother', 'Mère'),
        ('guardian', 'Tuteur/Tutrice'),
        ('other', 'Autre'),
    ], string='Relation', required=True, tracking=True)

    gender = fields.Selection([
        ('male', 'Masculin'),
        ('female', 'Féminin'),
    ], string='Sexe', tracking=True)

    date_of_birth = fields.Date(string='Date de naissance')

    # Informations de contact
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Téléphone', tracking=True)
    mobile = fields.Char(string='Mobile', tracking=True)

    # Adresse
    street = fields.Char(string='Rue')
    street2 = fields.Char(string='Rue 2')
    city = fields.Char(string='Ville')
    state_id = fields.Many2one('res.country.state', string='État')
    zip = fields.Char(string='Code postal')
    country_id = fields.Many2one('res.country', string='Pays')

    # Informations professionnelles
    occupation = fields.Char(string='Profession', tracking=True)
    company_name = fields.Char(string='Entreprise')
    work_phone = fields.Char(string='Téléphone professionnel')
    work_email = fields.Char(string='Email professionnel')

    # Étudiants
    student_ids = fields.Many2many(
        'silina.student',
        'student_parent_rel',
        'parent_id',
        'student_id',
        string='Étudiants'
    )
    student_count = fields.Integer(
        string='Nombre d\'étudiants',
        compute='_compute_student_count'
    )

    # Contact d'urgence
    is_emergency_contact = fields.Boolean(
        string='Contact d\'urgence',
        default=True,
        help="Peut être contacté en cas d'urgence"
    )

    # Autorisation de prise en charge
    can_pickup = fields.Boolean(
        string='Autorisé à récupérer l\'enfant',
        default=True
    )

    # Informations financières
    is_financial_responsible = fields.Boolean(
        string='Responsable financier',
        default=False,
        help="Responsable du paiement des frais scolaires"
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Contact lié',
        help="Contact Odoo lié pour la facturation"
    )

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    @api.depends('student_ids')
    def _compute_student_count(self):
        for record in self:
            record.student_count = len(record.student_ids)

    def action_view_students(self):
        self.ensure_one()
        return {
            'name': _('Étudiants'),
            'type': 'ir.actions.act_window',
            'res_model': 'silina.student',
            'view_mode': 'list,form',
            'domain': [('parent_ids', 'in', self.ids)],
        }

    def action_create_partner(self):
        """Créer un contact res.partner pour la facturation"""
        self.ensure_one()
        if self.partner_id:
            raise ValidationError(_('Un contact existe déjà pour ce parent!'))

        partner_vals = {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'mobile': self.mobile,
            'street': self.street,
            'street2': self.street2,
            'city': self.city,
            'state_id': self.state_id.id,
            'zip': self.zip,
            'country_id': self.country_id.id,
            'comment': f'Parent/Tuteur - {self.relation}',
        }
        partner = self.env['res.partner'].create(partner_vals)
        self.partner_id = partner.id

        return {
            'name': _('Contact'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }
