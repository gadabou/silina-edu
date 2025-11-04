from odoo import models, fields, api


class Dashboard(models.Model):
    _name = 'silina.dashboard'
    _description = 'Tableau de Bord Scolaire'
    _rec_name = 'current_academic_year_id'

    # Statistiques générales des élèves
    total_students = fields.Integer(
        string='Total Élèves',
        compute='_compute_student_stats'
    )
    male_students = fields.Integer(
        string='Élèves Masculins',
        compute='_compute_student_stats'
    )
    female_students = fields.Integer(
        string='Élèves Féminins',
        compute='_compute_student_stats'
    )

    # Statistiques par état
    enrolled_students = fields.Integer(
        string='Élèves Inscrits',
        compute='_compute_student_stats'
    )

    # Statistiques financières
    total_students_with_debt = fields.Integer(
        string='Élèves avec Dettes',
        compute='_compute_financial_stats'
    )
    total_debt_amount = fields.Monetary(
        string='Montant Total des Dettes',
        compute='_compute_financial_stats',
        currency_field='currency_id'
    )
    total_paid_amount = fields.Monetary(
        string='Montant Total Payé',
        compute='_compute_financial_stats',
        currency_field='currency_id'
    )
    total_expected_amount = fields.Monetary(
        string='Montant Total Attendu',
        compute='_compute_financial_stats',
        currency_field='currency_id'
    )
    payment_rate = fields.Float(
        string='Taux de Paiement (%)',
        compute='_compute_financial_stats'
    )

    # Caisse (trésorerie)
    cash_balance = fields.Monetary(
        string='Solde de Caisse',
        compute='_compute_cash_stats',
        currency_field='currency_id',
        help="Solde actuel dans les comptes de trésorerie"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id
    )

    # Statistiques par niveau
    stats_by_level_ids = fields.One2many(
        'silina.dashboard.level.stats',
        'dashboard_id',
        string='Statistiques par Niveau'
    )

    # Statistiques par classe
    stats_by_classroom_ids = fields.One2many(
        'silina.dashboard.classroom.stats',
        'dashboard_id',
        string='Statistiques par Classe'
    )

    # Statistiques du personnel
    total_teachers = fields.Integer(
        string='Total Enseignants',
        compute='_compute_staff_stats'
    )
    total_employees = fields.Integer(
        string='Total Employés',
        compute='_compute_staff_stats'
    )
    total_departments = fields.Integer(
        string='Total Départements',
        compute='_compute_staff_stats'
    )

    # Année scolaire courante
    current_academic_year_id = fields.Many2one(
        'silina.academic.year',
        string='Année Scolaire',
        default=lambda self: self.env['silina.academic.year'].get_current_year()
    )

    @api.depends('current_academic_year_id')
    def _compute_student_stats(self):
        """Calcul des statistiques générales des élèves"""
        for record in self:
            domain = [('active', '=', True)]
            if record.current_academic_year_id:
                domain.append(('academic_year_id', '=', record.current_academic_year_id.id))

            Student = self.env['silina.student']

            # Total des élèves
            record.total_students = Student.search_count(domain)

            # Par sexe
            record.male_students = Student.search_count(domain + [('gender', '=', 'male')])
            record.female_students = Student.search_count(domain + [('gender', '=', 'female')])

            # Élèves inscrits (état = enrolled)
            record.enrolled_students = Student.search_count(domain + [('state', '=', 'enrolled')])

    @api.depends('current_academic_year_id')
    def _compute_financial_stats(self):
        """Calcul des statistiques financières"""
        for record in self:
            domain = [
                ('move_type', '=', 'out_invoice'),
                ('state', '!=', 'cancel')
            ]

            if record.current_academic_year_id:
                # Filtrer par année scolaire si disponible
                domain.append(('invoice_date', '>=', record.current_academic_year_id.date_start))
                domain.append(('invoice_date', '<=', record.current_academic_year_id.date_end))

            Invoice = self.env['account.move']
            invoices = Invoice.search(domain)

            # Calculer les montants
            total_expected = sum(invoices.mapped('amount_total'))
            total_paid = sum(invoices.mapped('amount_total')) - sum(invoices.mapped('amount_residual'))
            total_debt = sum(invoices.mapped('amount_residual'))

            record.total_expected_amount = total_expected
            record.total_paid_amount = total_paid
            record.total_debt_amount = total_debt

            # Calculer le taux de paiement
            if total_expected > 0:
                record.payment_rate = (total_paid / total_expected) * 100
            else:
                record.payment_rate = 0.0

            # Compter les élèves avec dettes (factures impayées)
            invoices_with_debt = invoices.filtered(lambda inv: inv.amount_residual > 0)
            partner_ids_with_debt = invoices_with_debt.mapped('partner_id.id')

            # Trouver les élèves correspondant à ces partenaires
            students_with_debt = self.env['silina.student'].search([
                ('partner_id', 'in', partner_ids_with_debt),
                ('active', '=', True)
            ])

            record.total_students_with_debt = len(students_with_debt)

    def _compute_cash_stats(self):
        """Calcul des statistiques de caisse"""
        for record in self:
            # Rechercher les comptes de type liquidity (comptes de banque et caisse)
            try:
                liquidity_accounts = self.env['account.account'].search([
                    ('account_type', '=', 'asset_cash')
                ])

                # Calculer le solde total
                cash_balance = 0.0
                for account in liquidity_accounts:
                    if hasattr(account, 'current_balance'):
                        cash_balance += account.current_balance
                    elif hasattr(account, 'balance'):
                        cash_balance += account.balance

                record.cash_balance = cash_balance
            except Exception:
                # En cas d'erreur, mettre le solde à 0
                record.cash_balance = 0.0

    def _generate_level_stats(self):
        """Génère les statistiques par niveau"""
        self.ensure_one()
        # Supprimer les anciennes statistiques
        self.stats_by_level_ids.unlink()

        domain = [('active', '=', True)]
        if self.current_academic_year_id:
            domain.append(('academic_year_id', '=', self.current_academic_year_id.id))

        # Récupérer tous les niveaux
        levels = self.env['silina.level'].search([])

        for level in levels:
            students = self.env['silina.student'].search(
                domain + [('level_id', '=', level.id)]
            )

            if students:
                male_count = len(students.filtered(lambda s: s.gender == 'male'))
                female_count = len(students.filtered(lambda s: s.gender == 'female'))

                self.env['silina.dashboard.level.stats'].create({
                    'dashboard_id': self.id,
                    'level_id': level.id,
                    'total_students': len(students),
                    'male_students': male_count,
                    'female_students': female_count,
                })

    def _generate_classroom_stats(self):
        """Génère les statistiques par classe"""
        self.ensure_one()
        # Supprimer les anciennes statistiques
        self.stats_by_classroom_ids.unlink()

        domain = []
        if self.current_academic_year_id:
            domain.append(('academic_year_id', '=', self.current_academic_year_id.id))

        # Récupérer toutes les classes
        classrooms = self.env['silina.classroom'].search(domain)

        for classroom in classrooms:
            students = self.env['silina.student'].search([
                ('classroom_id', '=', classroom.id),
                ('active', '=', True)
            ])

            if students:
                male_count = len(students.filtered(lambda s: s.gender == 'male'))
                female_count = len(students.filtered(lambda s: s.gender == 'female'))

                self.env['silina.dashboard.classroom.stats'].create({
                    'dashboard_id': self.id,
                    'classroom_id': classroom.id,
                    'total_students': len(students),
                    'male_students': male_count,
                    'female_students': female_count,
                })

    def _compute_staff_stats(self):
        """Calcul des statistiques du personnel"""
        for record in self:
            # Compter les enseignants (modèle silina.teacher)
            teachers = self.env['silina.teacher'].search([('active', '=', True)])
            record.total_teachers = len(teachers)

            # Compter tous les employés (modèle hr.employee)
            employees = self.env['hr.employee'].search([('active', '=', True)])
            record.total_employees = len(employees)

            # Compter les départements
            departments = self.env['hr.department'].search([])
            record.total_departments = len(departments)

    @api.model
    def get_dashboard(self):
        """Récupère ou crée le tableau de bord pour l'année scolaire courante"""
        current_year = self.env['silina.academic.year'].get_current_year()
        dashboard = self.search([('current_academic_year_id', '=', current_year.id)], limit=1)

        if not dashboard:
            dashboard = self.create({
                'current_academic_year_id': current_year.id,
            })
            dashboard.action_refresh()

        return dashboard

    def action_refresh(self):
        """Rafraîchir les statistiques"""
        self.ensure_one()
        # Forcer le recalcul de tous les champs computed
        self._compute_student_stats()
        self._compute_financial_stats()
        self._compute_cash_stats()
        self._compute_staff_stats()

        # Générer les statistiques par niveau et classe
        self._generate_level_stats()
        self._generate_classroom_stats()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Tableau de bord actualisé',
                'message': 'Les statistiques ont été mises à jour avec succès.',
                'type': 'success',
                'sticky': False,
            }
        }


class DashboardLevelStats(models.Model):
    _name = 'silina.dashboard.level.stats'
    _description = 'Statistiques par Niveau'
    _order = 'level_id'

    dashboard_id = fields.Many2one('silina.dashboard', string='Tableau de bord', ondelete='cascade')
    level_id = fields.Many2one('silina.level', string='Niveau', required=True)
    total_students = fields.Integer(string='Total Élèves')
    male_students = fields.Integer(string='Garçons')
    female_students = fields.Integer(string='Filles')


class DashboardClassroomStats(models.Model):
    _name = 'silina.dashboard.classroom.stats'
    _description = 'Statistiques par Classe'
    _order = 'classroom_id'

    dashboard_id = fields.Many2one('silina.dashboard', string='Tableau de bord', ondelete='cascade')
    classroom_id = fields.Many2one('silina.classroom', string='Classe', required=True)
    total_students = fields.Integer(string='Total Élèves')
    male_students = fields.Integer(string='Garçons')
    female_students = fields.Integer(string='Filles')
