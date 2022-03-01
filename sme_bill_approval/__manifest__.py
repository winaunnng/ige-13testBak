# -*- coding: utf-8 -*-
{
    'name': "SMEi Bill/Journal Entry Approval",

    'summary': """
        Bill/Journal Entry Approval""",

    'description': """
        Bill/Journal Entry Approval
    """,

    'author': "SME Intellect Co. Ltd",
    'website': "https://www.smeintellect.com/",
    'category': 'Account Management',
    'version': '0.1',

    'depends': ['account'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/account_move_refuse_reason_views.xml',
        'views/account_move_view.xml',
        'views/res_config_settings_view.xml',
        'data/mail_activity_data.xml',

    ],
    'license': 'LGPL-3',
}
