# -*- coding: utf-8 -*-
{
    'name': "SMEi Approval Approval",

    'summary': """
        Create and validate approvals requests""",

    'description': """
        Create and validate approvals requests
    """,

    'author': "SME Intellect Co. Ltd",
    'website': "https://www.smeintellect.com/",
    'category': 'Human Resources/Approvals',
    'version': '0.1',

    'depends': ['approvals'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/approval_refuse_reason.xml',
        'views/approval_views.xml',
        'data/approval_category_data.xml',
    ],
    'license': 'LGPL-3',
}
