from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StudentFeePayment(models.TransientModel):
    _name = 'silina.student.fee.payment.wizard'
    _description = 'Paiement des Frais Scolaires'

    student_id = fields.Many2one(
        'silina.student',
        string='Élève',
        required=True,
        domain="[('state', '=', 'enrolled')]"
    )

    fee_type_id = fields.Many2one(
        'silina.fee.type',
        string='Type de frais',
        required=True
    )

    installment_id = fields.Many2one(
        'silina.fee.type.installment',
        string='Tranche à payer',
        domain="[('fee_type_id', '=', fee_type_id)]"
    )

    payment_type = fields.Selection([
        ('full', 'Paiement complet'),
        ('installment', 'Paiement par tranche'),
    ], string='Type de paiement', default='full', required=True)

    amount = fields.Monetary(
        string='Montant à payer',
        required=True,
        currency_field='currency_id',
        compute='_compute_amount',
        readonly=False,
        store=True
    )

    payment_method = fields.Selection([
        ('cash', 'Espèces'),
        ('bank_transfer', 'Virement bancaire'),
        ('check', 'Chèque'),
        ('mobile_money', 'Mobile Money'),
    ], string='Mode de paiement', default='cash', required=True)

    payment_date = fields.Date(
        string='Date de paiement',
        default=fields.Date.today,
        required=True
    )

    reference = fields.Char(
        string='Référence de paiement',
        help="Numéro de chèque, référence de virement, etc."
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id
    )

    notes = fields.Text(string='Notes')

    # Informations sur les factures existantes
    existing_invoices = fields.Boolean(
        string='Factures existantes',
        compute='_compute_existing_invoices'
    )

    unpaid_amount = fields.Monetary(
        string='Montant impayé',
        compute='_compute_existing_invoices',
        currency_field='currency_id'
    )

    overdue_invoices_count = fields.Integer(
        string='Factures en retard',
        compute='_compute_existing_invoices'
    )

    @api.depends('fee_type_id', 'payment_type', 'installment_id')
    def _compute_amount(self):
        for record in self:
            if record.payment_type == 'installment' and record.installment_id:
                record.amount = record.installment_id.amount
            elif record.payment_type == 'full' and record.fee_type_id:
                record.amount = sum(record.fee_type_id.installment_ids.mapped('amount'))
            else:
                record.amount = 0.0

    @api.depends('student_id', 'fee_type_id')
    def _compute_existing_invoices(self):
        for record in self:
            if record.student_id and record.fee_type_id:
                # Chercher les factures existantes pour cet élève et ce type de frais
                invoices = self.env['account.move'].search([
                    ('partner_id', '=', record.student_id.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ['not_paid', 'partial']),
                    ('invoice_line_ids.product_id', '=', record.fee_type_id.product_id.id),
                ])
                record.existing_invoices = bool(invoices)
                record.unpaid_amount = sum(invoices.mapped('amount_residual'))

                # Compter les factures en retard
                today = fields.Date.today()
                overdue = invoices.filtered(lambda inv: inv.invoice_date_due and inv.invoice_date_due < today)
                record.overdue_invoices_count = len(overdue)
            else:
                record.existing_invoices = False
                record.unpaid_amount = 0.0
                record.overdue_invoices_count = 0

    @api.onchange('fee_type_id')
    def _onchange_fee_type_id(self):
        """Réinitialiser la tranche quand on change le type de frais"""
        self.installment_id = False

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """Adapter le montant selon le type de paiement"""
        if self.payment_type == 'full':
            self.installment_id = False

    def action_process_payment(self):
        """Traiter le paiement : créer la facture et enregistrer le paiement"""
        self.ensure_one()

        # Vérifier que l'élève a un partner
        if not self.student_id.partner_id:
            self.student_id._create_partner()

        # Chercher ou créer la facture
        invoice = self._get_or_create_invoice()

        # Enregistrer le paiement
        payment = self._register_payment(invoice)

        # Générer le reçu de paiement
        return self._generate_receipt(payment, invoice)

    def _get_or_create_invoice(self):
        """Récupérer ou créer la facture appropriée"""
        # Chercher une facture existante non payée
        if self.payment_type == 'installment' and self.installment_id:
            # Chercher la facture de cette tranche spécifique
            invoice = self.env['account.move'].search([
                ('partner_id', '=', self.student_id.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('invoice_origin', 'ilike', self.installment_id.name),
            ], limit=1)

            if not invoice:
                # Créer une facture pour cette tranche
                invoice = self._create_installment_invoice()
        else:
            # Paiement complet : vérifier s'il y a des factures impayées
            invoices = self.env['account.move'].search([
                ('partner_id', '=', self.student_id.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('invoice_line_ids.product_id', '=', self.fee_type_id.product_id.id),
            ])

            if not invoices:
                # Créer toutes les factures pour toutes les tranches
                invoice = self._create_full_invoices()
            else:
                invoice = invoices[0]

        return invoice

    def _create_installment_invoice(self):
        """Créer une facture pour une tranche spécifique"""
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.student_id.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_date_due': self.installment_id.due_date if self.installment_id.due_date_type == 'fixed' else fields.Date.today(),
            'invoice_origin': f"{self.fee_type_id.name} - {self.installment_id.name}",
            'invoice_line_ids': [(0, 0, {
                'product_id': self.fee_type_id.product_id.id,
                'name': f"{self.fee_type_id.name} - {self.installment_id.name}\nÉlève: {self.student_id.name}\nMatricule: {self.student_id.registration_number}\nClasse: {self.student_id.classroom_id.name if self.student_id.classroom_id else 'N/A'}",
                'quantity': 1,
                'price_unit': self.installment_id.amount,
            })],
        }

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        return invoice

    def _create_full_invoices(self):
        """Créer toutes les factures pour toutes les tranches"""
        invoices = self.env['account.move']
        for installment in self.fee_type_id.installment_ids:
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': self.student_id.partner_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': installment.due_date if installment.due_date_type == 'fixed' else fields.Date.today(),
                'invoice_origin': f"{self.fee_type_id.name} - {installment.name}",
                'invoice_line_ids': [(0, 0, {
                    'product_id': self.fee_type_id.product_id.id,
                    'name': f"{self.fee_type_id.name} - {installment.name}\nÉlève: {self.student_id.name}\nMatricule: {self.student_id.registration_number}\nClasse: {self.student_id.classroom_id.name if self.student_id.classroom_id else 'N/A'}",
                    'quantity': 1,
                    'price_unit': installment.amount,
                })],
            }
            invoice = self.env['account.move'].create(invoice_vals)
            invoice.action_post()
            invoices |= invoice

        return invoices[0] if invoices else False

    def _register_payment(self, invoice):
        """Enregistrer le paiement sur la facture"""
        # Créer le paiement via le wizard standard d'Odoo
        payment_vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.student_id.partner_id.id,
            'amount': self.amount,
            'date': self.payment_date,
            'ref': self.reference or f"Paiement {self.fee_type_id.name} - {self.student_id.name}",
            'journal_id': self._get_payment_journal().id,
        }

        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()

        # Réconcilier avec la facture
        lines_to_reconcile = (invoice.line_ids + payment.move_id.line_ids).filtered(
            lambda line: line.account_id == invoice.line_ids[0].account_id and not line.reconciled
        )
        lines_to_reconcile.reconcile()

        return payment

    def _get_payment_journal(self):
        """Récupérer le journal de paiement approprié"""
        journal_type = 'cash' if self.payment_method == 'cash' else 'bank'
        journal = self.env['account.journal'].search([
            ('type', '=', journal_type),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not journal:
            raise ValidationError(_(
                f'Aucun journal de type {journal_type} trouvé! '
                'Veuillez configurer un journal de paiement.'
            ))

        return journal

    def _generate_receipt(self, payment, invoice):
        """Générer et afficher le reçu de paiement"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reçu de paiement'),
            'res_model': 'account.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'current',
        }
