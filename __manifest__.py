{
    'name': 'SILINA-EDU - Gestion Scolaire',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'Module complet de gestion d\'un complexe scolaire (Primaire, Collège, Lycée)',
    'description': """
        SILINA-EDU - Système de Gestion Scolaire Intégré
        =================================================
        
        Fonctionnalités principales:
        * Gestion des élèves et parents/tuteurs
        * Gestion des classes et niveaux (Primaire, Collège, Lycée)
        * Gestion des enseignants et matières
        * Gestion des examens et résultats
        * Génération automatique des bulletins de notes (plusieurs modèles)
        * Gestion des frais scolaires avec paiements par tranches
        * Gestion des documents élèves
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
        'security/payroll_access.xml',

        # Data
        'data/sequence_data.xml',
        'data/academic_data.xml',

        # Views - Separated by model
        'views/academic_year_views.xml',
        'views/level_views.xml',
        'views/classroom_views.xml',
        'views/subject_views.xml',
        'views/subject_assignment_views.xml',
        'views/teacher_views.xml',
        'views/student_views.xml',
        'views/parent_views.xml',
        'views/student_document_views.xml',
        'views/exam_views.xml',
        'views/exam_result_views.xml',
        'views/fee_type_views.xml',
        'views/payroll_views.xml',

        # Wizards (must be loaded before menus that reference them)
        'wizards/bulk_student_promotion_views.xml',
        'wizards/generate_report_card_views.xml',
        'wizards/generate_fee_invoices_views.xml',
        'wizards/student_fee_payment_views.xml',

        # Menus (loaded after wizards)
        'views/menu_views.xml',

        # Reports
        'reports/invoice_report_template.xml',
        'reports/invoice_enhanced_template.xml',
        'reports/payment_receipt_template.xml',
        'reports/report_card_template.xml',
        'reports/student_list_template.xml',
    ],
    'demo': [],
    'assets': {
        'web.assets_backend': [
            'silina_edu/static/src/css/silina_edu.css',
        ],
        'web.report_assets_common': [
            'silina_edu/static/src/css/report_styles.css',
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

