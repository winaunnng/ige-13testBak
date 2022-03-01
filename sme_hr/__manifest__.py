# -*- coding: utf-8 -*-
{
    'name': "SMEi Human Resources",

    'summary': """
        HR Managment""",

    'description': """
       HR Managment
    """,

    'author': "SME Intellect Co. Ltd",
    'website': "https://www.smeintellect.com/",
    'category': 'HR Management',
    'version': '0.1',

    'depends': ['hr','hr_payroll','hr_recruitment'],

    'data': [
       #  'report/hr_report.xml',
        'views/hr_employee_view.xml',
        'views/hr_recruitment_view.xml',
        'security/ir.model.access.csv',
        'data/hr_warning_scheduler.xml',
        'data/ir_config_param.xml',
        'data/mail_data.xml',

    ],
    'license': 'LGPL-3',

}
