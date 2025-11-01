# -*- coding: utf-8 -*-
{
    'name': "School Fees",

    'summary': """
    Fee Management
        """,

    'description': """
        Fees Managment
    """,

    'author': "Dynexcel",
    'website': "https://www.dynexcel.com",

    'category': 'Dynexcel',
    'version': '16.0.0.1',
    'installable': True,
    'application': True,
    # any module necessary for this one to work correctly
    'depends': ['de_school','account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/fee_data.xml',
        'data/feeslip_sequence.xml',
        'views/fees_menu.xml',
        'views/fee_category_views.xml',
        'views/fee_rule_views.xml',
        'views/fee_struct_views.xml',
        'views/feeslip_input_type_views.xml',
        'views/feeslip_views.xml',
        'wizard/feeslip_by_students_views.xml',
        'views/feeslip_run_views.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
