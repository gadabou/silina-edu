from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class GenerateFeeInvoices(models.TransientModel):
    _name = 'silina.generate.fee.invoices.wizard'
    _description = 'Assistant de Génération de Factures de Frais'

    fee_type_id = fields.Many2one(
        'silina.fee.type',
        string='Type de frais',
        required=True
    )

    academic_year_id = fields.Many2one(
        'silina.academic.year',
        string='Année scolaire',
        required=True,
        default=lambda self: self.env['silina.academic.year'].get_current_year()
    )

    generation_mode = fields.Selection([
        ('all', 'Tous les élèves éligibles'),
        ('classroom', 'Par classe'),
        ('student', 'Par élève'),
    ], string='Mode de génération', default='all', required=True)

    classroom_ids = fields.Many2many(
        'silina.classroom',
        'gen_invoice_classroom_rel',
        'wizard_id',
        'classroom_id',
        string='Classes',
        domain="[('academic_year_id', '=', academic_year_id)]"
    )

    student_ids = fields.Many2many(
        'silina.student',
        'gen_invoice_student_rel',
        'wizard_id',
        'student_id',
        string='Élèves',
        domain="[('state', '=', 'enrolled')]"
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Contact par défaut',
        help="Contact à utiliser si aucun parent responsable financier n'est trouvé"
    )

    start_date = fields.Date(
        string='Date de début',
        default=fields.Date.today,
        help="Date de début pour le calcul des échéances relatives"
    )

    student_count = fields.Integer(
        string='Nombre d\'élèves',
        compute='_compute_student_count'
    )

    @api.depends('student_ids', 'classroom_ids', 'generation_mode')
    def _compute_student_count(self):
        for record in self:
            if record.generation_mode == 'student':
                record.student_count = len(record.student_ids)
            elif record.generation_mode == 'classroom':
                students = self.env['silina.student'].search([
                    ('classroom_id', 'in', record.classroom_ids.ids),
                    ('state', '=', 'enrolled')
                ])
                record.student_count = len(students)
            else:
                # Tous les élèves du niveau concerné
                level_ids = record.fee_type_id.level_ids.ids
                students = self.env['silina.student'].search([
                    ('level_id', 'in', level_ids),
                    ('academic_year_id', '=', record.academic_year_id.id),
                    ('state', '=', 'enrolled')
                ])
                record.student_count = len(students)

    @api.onchange('generation_mode')
    def _onchange_generation_mode(self):
        if self.generation_mode == 'all':
            self.classroom_ids = False
            self.student_ids = False
        elif self.generation_mode == 'classroom':
            self.student_ids = False
        elif self.generation_mode == 'student':
            self.classroom_ids = False

    def action_generate_invoices(self):
        """Générer les factures pour les élèves sélectionnés"""
        self.ensure_one()

        if not self.fee_type_id.installment_ids:
            raise ValidationError(_(
                'Aucune tranche de paiement n\'est définie pour ce type de frais!'
            ))

        # Récupérer les élèves concernés
        students = self._get_students()

        if not students:
            raise ValidationError(_('Aucun élève éligible trouvé!'))

        # Générer les factures
        invoice_count = 0
        errors = []

        for student in students:
            try:
                # S'assurer que l'élève a un contact partner
                if not student.partner_id:
                    student._create_partner()

                # Vérifier si des factures existent déjà pour cet élève
                existing_invoices = self.env['account.move'].search([
                    ('partner_id', '=', student.partner_id.id),
                    ('invoice_line_ids.product_id', '=', self.fee_type_id.product_id.id),
                    ('state', 'in', ['draft', 'posted']),
                ])

                if existing_invoices:
                    errors.append(f"{student.name}: Des factures existent déjà")
                    continue

                # Créer une facture par tranche
                for installment in self.fee_type_id.installment_ids:
                    due_date = self._compute_due_date(installment)

                    invoice_vals = {
                        'move_type': 'out_invoice',
                        'partner_id': student.partner_id.id,  # Utiliser le contact de l'élève
                        'invoice_date': fields.Date.today(),
                        'invoice_date_due': due_date,
                        'invoice_origin': f"{self.fee_type_id.name} - {installment.name}",
                        'invoice_line_ids': [(0, 0, {
                            'product_id': self.fee_type_id.product_id.id,
                            'name': f"{self.fee_type_id.name} - {installment.name}\nÉlève: {student.name}\nMatricule: {student.registration_number}\nClasse: {student.classroom_id.name if student.classroom_id else 'N/A'}\nAnnée: {self.academic_year_id.name}",
                            'quantity': 1,
                            'price_unit': installment.amount,
                            'account_id': self.fee_type_id.account_id.id if self.fee_type_id.account_id else self.fee_type_id.product_id.categ_id.property_account_income_categ_id.id,
                        })],
                    }

                    invoice = self.env['account.move'].create(invoice_vals)
                    # Post the invoice immediately
                    invoice.action_post()
                    invoice_count += 1

            except Exception as e:
                errors.append(f"{student.name}: {str(e)}")

        # Afficher le résultat
        message = _('%s factures ont été créées avec succès.') % invoice_count
        if errors:
            message += '\n\n' + _('Erreurs:') + '\n' + '\n'.join(errors[:10])
            if len(errors) > 10:
                message += f"\n... et {len(errors) - 10} autres erreurs"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Génération de factures terminée'),
                'message': message,
                'type': 'success' if not errors else 'warning',
                'sticky': True,
            }
        }

    def _get_students(self):
        """Récupérer les élèves concernés selon le mode de génération"""
        if self.generation_mode == 'student':
            return self.student_ids
        elif self.generation_mode == 'classroom':
            return self.env['silina.student'].search([
                ('classroom_id', 'in', self.classroom_ids.ids),
                ('state', '=', 'enrolled')
            ])
        else:  # all
            level_ids = self.fee_type_id.level_ids.ids
            return self.env['silina.student'].search([
                ('level_id', 'in', level_ids),
                ('academic_year_id', '=', self.academic_year_id.id),
                ('state', '=', 'enrolled')
            ])

    def _get_partner_for_student(self, student):
        """Trouver le partenaire pour la facturation"""
        # Chercher un parent responsable financier
        for parent in student.parent_ids:
            if parent.is_financial_responsible and parent.partner_id:
                return parent.partner_id

        # Sinon utiliser le partenaire par défaut du wizard
        if self.partner_id:
            return self.partner_id

        return False

    def _compute_due_date(self, installment):
        """Calculer la date d'échéance selon le type"""
        if installment.due_date_type == 'fixed':
            return installment.due_date or fields.Date.today()
        else:  # relative
            return self.start_date + relativedelta(days=installment.due_days)
