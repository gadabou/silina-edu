from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class StudentFee(models.Model):
    _name = 'silina.student.fee'
    _description = 'Frais d\'Étudiant'
    _order = 'academic_year_id desc, student_id, fee_type_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True
    )

    student_id = fields.Many2one(
        'silina.student',
        string='Étudiant',
        required=True,
        ondelete='cascade',
        tracking=True
    )

    fee_type_id = fields.Many2one(
        'silina.fee.type',
        string='Type de frais',
        required=True,
        tracking=True
    )

    academic_year_id = fields.Many2one(
        'silina.academic.year',
        string='Année Scolaire',
        required=True,
        tracking=True,
        default=lambda self: self.env['silina.academic.year'].get_current_year()
    )

    classroom_id = fields.Many2one(
        related='student_id.classroom_id',
        string='Classe',
        store=True,
        readonly=True
    )

    # Montants
    amount = fields.Monetary(
        string='Montant total',
        required=True,
        currency_field='currency_id',
        tracking=True
    )
    amount_paid = fields.Monetary(
        string='Montant payé',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id'
    )
    amount_due = fields.Monetary(
        string='Montant dû',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id
    )

    # Tranches de paiement
    installment_ids = fields.One2many(
        'silina.fee.installment',
        'student_fee_id',
        string='Tranches'
    )
    installment_count = fields.Integer(
        string='Nombre de tranches',
        default=1
    )

    # Paiements
    payment_ids = fields.One2many(
        'silina.fee.payment',
        'student_fee_id',
        string='Paiements'
    )
    payment_count = fields.Integer(
        string='Nombre de paiements',
        compute='_compute_payment_count'
    )

    # Facturation
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        copy=False,
        readonly=True
    )

    due_date = fields.Date(
        string='Date d\'échéance',
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('partial', 'Partiellement payé'),
        ('paid', 'Payé'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', compute='_compute_state', store=True, tracking=True)

    description = fields.Text(string='Description')

    _sql_constraints = [
        ('fee_unique', 'unique(student_id, fee_type_id, academic_year_id)',
         'Ces frais existent déjà pour cet étudiant cette année!'),
    ]

    @api.depends('payment_ids', 'payment_ids.amount', 'payment_ids.state')
    def _compute_amounts(self):
        for record in self:
            paid_amount = sum(record.payment_ids.filtered(
                lambda p: p.state == 'paid'
            ).mapped('amount'))
            record.amount_paid = paid_amount
            record.amount_due = record.amount - paid_amount

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for record in self:
            record.payment_count = len(record.payment_ids)

    @api.depends('amount', 'amount_paid', 'amount_due')
    def _compute_state(self):
        for record in self:
            if record.state == 'cancelled':
                continue
            elif record.amount_due <= 0:
                record.state = 'paid'
            elif record.amount_paid > 0:
                record.state = 'partial'
            elif record.state == 'draft':
                record.state = 'draft'
            else:
                record.state = 'confirmed'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'silina.student.fee'
                ) or _('Nouveau')
        records = super().create(vals_list)

        # Créer les tranches si nécessaire
        for record in records:
            if record.installment_count > 1 and not record.installment_ids:
                record._create_installments()

        return records

    def _create_installments(self):
        """Créer les tranches de paiement"""
        self.ensure_one()
        if self.installment_count <= 1:
            return

        installment_amount = self.amount / self.installment_count
        installments = []

        for i in range(self.installment_count):
            due_date = self.due_date
            if due_date:
                due_date = due_date + relativedelta(months=i)

            installments.append({
                'student_fee_id': self.id,
                'name': f"Tranche {i+1}/{self.installment_count}",
                'sequence': i + 1,
                'amount': installment_amount,
                'due_date': due_date,
            })

        self.env['silina.fee.installment'].create(installments)

    def action_confirm(self):
        self.ensure_one()
        self.state = 'confirmed'
        return True

    def action_cancel(self):
        self.ensure_one()
        if self.payment_ids.filtered(lambda p: p.state == 'paid'):
            raise ValidationError(_('Impossible d\'annuler des frais avec des paiements confirmés!'))
        self.state = 'cancelled'
        return True

    def action_create_invoice(self):
        """Créer une facture pour ces frais"""
        self.ensure_one()
        if self.invoice_id:
            raise ValidationError(_('Une facture existe déjà pour ces frais!'))

        # Trouver le partenaire (parent responsable financier)
        partner = False
        for parent in self.student_id.parent_ids:
            if parent.is_financial_responsible and parent.partner_id:
                partner = parent.partner_id
                break

        if not partner:
            raise ValidationError(_(
                'Aucun parent avec un contact financier n\'a été trouvé pour cet étudiant!'
            ))

        # Créer la facture
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_date_due': self.due_date or fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.fee_type_id.product_id.id,
                'name': f"{self.fee_type_id.name} - {self.student_id.name} ({self.academic_year_id.name})",
                'quantity': 1,
                'price_unit': self.amount,
                'account_id': self.fee_type_id.account_id.id if self.fee_type_id.account_id else False,
            })],
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id

        return {
            'name': _('Facture'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return self.action_create_invoice()

        return {
            'name': _('Facture'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'name': _('Paiements'),
            'type': 'ir.actions.act_window',
            'res_model': 'silina.fee.payment',
            'view_mode': 'list,form',
            'domain': [('student_fee_id', '=', self.id)],
            'context': {
                'default_student_fee_id': self.id,
                'default_student_id': self.student_id.id,
            }
        }


class FeeInstallment(models.Model):
    _name = 'silina.fee.installment'
    _description = 'Tranche de Frais'
    _order = 'student_fee_id, sequence'

    student_fee_id = fields.Many2one(
        'silina.student.fee',
        string='Frais',
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string='Nom',
        required=True,
        help="Ex: Tranche 1/3"
    )

    sequence = fields.Integer(
        string='Séquence',
        required=True
    )

    amount = fields.Monetary(
        string='Montant',
        required=True,
        currency_field='currency_id'
    )
    amount_paid = fields.Monetary(
        string='Montant payé',
        compute='_compute_amount_paid',
        store=True,
        currency_field='currency_id'
    )
    amount_due = fields.Monetary(
        string='Montant dû',
        compute='_compute_amount_paid',
        store=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        related='student_fee_id.currency_id',
        string='Devise'
    )

    due_date = fields.Date(
        string='Date d\'échéance',
        required=True
    )

    payment_ids = fields.One2many(
        'silina.fee.payment',
        'installment_id',
        string='Paiements'
    )

    state = fields.Selection([
        ('pending', 'En attente'),
        ('partial', 'Partiellement payé'),
        ('paid', 'Payé'),
        ('overdue', 'En retard'),
    ], string='État', compute='_compute_state', store=True)

    @api.depends('payment_ids', 'payment_ids.amount', 'payment_ids.state')
    def _compute_amount_paid(self):
        for record in self:
            paid_amount = sum(record.payment_ids.filtered(
                lambda p: p.state == 'paid'
            ).mapped('amount'))
            record.amount_paid = paid_amount
            record.amount_due = record.amount - paid_amount

    @api.depends('amount_paid', 'amount_due', 'due_date')
    def _compute_state(self):
        today = fields.Date.today()
        for record in self:
            if record.amount_due <= 0:
                record.state = 'paid'
            elif record.amount_paid > 0:
                record.state = 'partial'
            elif record.due_date and record.due_date < today:
                record.state = 'overdue'
            else:
                record.state = 'pending'
