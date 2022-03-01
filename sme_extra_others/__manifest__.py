# -*- coding: utf-8 -*-
{
    'name': "SMEi Extra Others",

    'summary': """
        Account""",

    'description': """
       Account Management , MRP
    """,

    'author': "SME Intellect Co. Ltd",
    'website': "https://www.smeintellect.com/",
    'category': 'Account Management',
    'version': '0.1',

    'depends': ['account','mrp','stock'],

    'data': [
        'data/cost_share_data.xml',
        'views/stock_views.xml'
    ],
    'license': 'LGPL-3',

}
