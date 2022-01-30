# -*- coding: utf-8 -*-
{
    'name': "SMEi Payment Approval",

    'summary': """
        Payment Approval""",

    'description': """
        Advance Payment Approval
    """,

    'author': "SME Intellect Co. Ltd",
    'website': "https://www.smeintellect.com/",
    'category': 'Accounting',
    'version': '0.1',
    'depends': ['account','purchase'],

    'data': [
        'security/account_payment_security.xml',
        'security/ir.model.access.csv',
        'wizard/payment_refuse_reason_view.xml',
        'views/account_payment_view.xml',
        'views/res_user_views.xml',
        'data/mail_activity_data.xml',
        'views/res_config_settings_view.xml'
    ],

}
