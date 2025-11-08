from odoo import models, fields, api, _


class Level(models.Model):
    _name = 'silina.level'
    _description = 'Niveau Scolaire'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nom',
        required=True,
        help="Ex: CP1, CP2, CE1, 6ème, 5ème, etc."
    )
    code = fields.Char(string='Code', required=True)

    degree = fields.Selection([
        ('daycare', 'Crèche'),
        ('preschool', 'Préscolaire'),
        ('primary', 'Primaire'),
        ('middle', 'Collège'),
        ('high', 'Lycée'),
    ], string='Degré', required=True)

    sequence = fields.Integer(
        string='Séquence',
        default=10,
        help="Ordre d'affichage"
    )

    next_level_id = fields.Many2one(
        'silina.level',
        string='Niveau suivant',
        help="Niveau supérieur pour le passage automatique"
    )

    description = fields.Text(string='Description')

    # Compteurs
    classroom_count = fields.Integer(
        string='Nombre de classes',
        compute='_compute_classroom_count'
    )

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Le code du niveau doit être unique!'),
    ]

    def _compute_classroom_count(self):
        for record in self:
            record.classroom_count = self.env['silina.classroom'].search_count([
                ('level_id', '=', record.id)
            ])

    @api.depends('name', 'code')
    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result
