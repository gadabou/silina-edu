from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Payroll(models.Model):
    _name = 'silina.payroll'
    _description = 'Fiche de Paie'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau')
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True,
        tracking=True
    )

    department_id = fields.Many2one(
        related='employee_id.department_id',
        string='Département',
        store=True,
        readonly=True
    )

    job_id = fields.Many2one(
        related='employee_id.job_id',
        string='Poste',
        store=True,
        readonly=True
    )

    date = fields.Date(
        string='Date de paie',
        required=True,
        default=fields.Date.today,
        tracking=True
    )

    period_start = fields.Date(
        string='Début de période',
        required=True,
        tracking=True
    )

    period_end = fields.Date(
        string='Fin de période',
        required=True,
        tracking=True
    )

    # Éléments de salaire
    basic_salary = fields.Monetary(
        string='Salaire de base',
        required=True,
        currency_field='currency_id',
        tracking=True
    )

    allowances = fields.Monetary(
        string='Primes et indemnités',
        currency_field='currency_id',
        help="Total des primes (transport, logement, etc.)"
    )

    overtime_amount = fields.Monetary(
        string='Heures supplémentaires',
        currency_field='currency_id'
    )

    bonus = fields.Monetary(
        string='Bonus',
        currency_field='currency_id'
    )

    gross_salary = fields.Monetary(
        string='Salaire brut',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id'
    )

    # Déductions
    social_security = fields.Monetary(
        string='Cotisations sociales',
        currency_field='currency_id',
        help="Cotisations sociales et assurances"
    )

    tax = fields.Monetary(
        string='Impôts',
        currency_field='currency_id'
    )

    other_deductions = fields.Monetary(
        string='Autres déductions',
        currency_field='currency_id',
        help="Avances, prêts, retenues, etc."
    )

    total_deductions = fields.Monetary(
        string='Total déductions',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id'
    )

    net_salary = fields.Monetary(
        string='Salaire net',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    # Informations de paiement
    payment_method = fields.Selection([
        ('cash', 'Espèces'),
        ('bank_transfer', 'Virement bancaire'),
        ('check', 'Chèque'),
        ('mobile_money', 'Mobile Money'),
    ], string='Mode de paiement', default='bank_transfer')

    payment_date = fields.Date(
        string='Date de paiement effectif',
        tracking=True
    )

    payment_reference = fields.Char(
        string='Référence de paiement',
        help="Numéro de chèque, référence de virement, etc."
    )

    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('paid', 'Payé'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True)

    # Facture fournisseur associée (optionnel)
    bill_id = fields.Many2one(
        'account.move',
        string='Facture fournisseur',
        readonly=True,
        help="Facture fournisseur générée pour cette paie"
    )

    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'La référence doit être unique!'),
    ]

    @api.depends('basic_salary', 'allowances', 'overtime_amount', 'bonus',
                 'social_security', 'tax', 'other_deductions')
    def _compute_amounts(self):
        for record in self:
            record.gross_salary = (
                record.basic_salary +
                record.allowances +
                record.overtime_amount +
                record.bonus
            )
            record.total_deductions = (
                record.social_security +
                record.tax +
                record.other_deductions
            )
            record.net_salary = record.gross_salary - record.total_deductions

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'silina.payroll'
                ) or _('Nouveau')
        return super().create(vals_list)

    @api.constrains('period_start', 'period_end')
    def _check_period(self):
        for record in self:
            if record.period_start and record.period_end:
                if record.period_start > record.period_end:
                    raise ValidationError(_(
                        'La date de début de période doit être antérieure à la date de fin!'
                    ))

    def action_confirm(self):
        """Confirmer la fiche de paie"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_('Seules les fiches en brouillon peuvent être confirmées!'))
        self.state = 'confirmed'
        return True

    def action_mark_paid(self):
        """Marquer comme payé"""
        self.ensure_one()
        if self.state != 'confirmed':
            raise ValidationError(_('Seules les fiches confirmées peuvent être marquées comme payées!'))
        self.payment_date = fields.Date.today()
        self.state = 'paid'
        return True

    def action_cancel(self):
        """Annuler la fiche de paie"""
        self.ensure_one()
        if self.state == 'paid':
            raise ValidationError(_('Une fiche payée ne peut pas être annulée!'))
        self.state = 'cancelled'
        return True

    def action_reset_to_draft(self):
        """Remettre en brouillon"""
        self.ensure_one()
        if self.state == 'paid':
            raise ValidationError(_('Une fiche payée ne peut pas être remise en brouillon!'))
        self.state = 'draft'
        return True

    def action_create_bill(self):
        """Créer une facture fournisseur pour cette paie (optionnel)"""
        self.ensure_one()
        if self.bill_id:
            raise ValidationError(_('Une facture existe déjà pour cette fiche de paie!'))

        if not self.employee_id.address_home_id:
            raise ValidationError(_(
                'Aucun contact privé n\'est défini pour cet employé! '
                'Veuillez d\'abord créer un contact pour l\'employé.'
            ))

        # Créer la facture fournisseur
        bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.employee_id.address_home_id.id,
            'invoice_date': self.date,
            'invoice_date_due': self.date,
            'invoice_origin': self.name,
            'invoice_line_ids': [(0, 0, {
                'name': f"Salaire {self.period_start} - {self.period_end}\nEmployé: {self.employee_id.name}",
                'quantity': 1,
                'price_unit': self.net_salary,
            })],
        }

        bill = self.env['account.move'].create(bill_vals)
        self.bill_id = bill.id

        return {
            'name': _('Facture fournisseur'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
            'target': 'current',
        }
