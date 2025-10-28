{
    'name': 'SILINA-EDU - Gestion Scolaire',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'Module complet de gestion d\'un complexe scolaire (Primaire, Collège, Lycée)',
    'description': """
        SILINA-EDU - Système de Gestion Scolaire Intégré
        =================================================

        Fonctionnalités principales:
        * Gestion des étudiants et parents/tuteurs
        * Gestion des classes et niveaux (Primaire, Collège, Lycée)
        * Gestion des enseignants et matières
        * Gestion des examens et résultats
        * Génération automatique des bulletins de notes (plusieurs modèles)
        * Gestion des frais scolaires avec paiements par tranches
        * Gestion des documents étudiants
        * Passage en masse des élèves en classe supérieure
        * Intégration avec la facturation pour les frais scolaires
        * Intégration avec Point de Vente pour articles scolaires
    """,
    'author': 'Djakpo GADO',
    'website': 'https://www.silinatech.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'point_of_sale',
        'account',
        'mail',
        'web',
    ],
    'data': [
        # Security
        'security/silina_edu_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence_data.xml',
        'data/academic_data.xml',

        # Views - All views in one file
        'views/all_views.xml',
        'views/academic_year_views.xml',

        # Wizards
        'wizards/bulk_student_promotion_views.xml',
        'wizards/generate_report_card_views.xml',
        'wizards/generate_student_fees_views.xml',

        # Reports
        'reports/report_card_template.xml',
        'reports/fee_receipt_template.xml',
        'reports/student_list_template.xml',

        # Menus (must be last)
        'views/menu_views.xml',
    ],
    'demo': [],
    'assets': {
        'web.assets_backend': [
            'silina_edu/static/src/css/silina_edu.css',
        ],
    },
    'images': [
        'static/description/icon.png',
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
