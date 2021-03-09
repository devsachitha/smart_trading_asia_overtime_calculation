# -*- coding: utf-8 -*-
{
    'name': "Smart Trading Asia Overtime Calculation",
    'summary': """
       Overtime Calc & Approvals """,
    'description': """
       Normal OT & Double OT
    """,
    'author': "Codeso",
    'website': "https://codeso.lk",
    'license':'Other proprietary',
    'category': 'Employees',
    'version': '1.0.0',
    'depends': ['hr','base'],
    'data': [
        'views/codeso_overtime.xml',
        'views/hr_department_inherit.xml',
        'data/overtime_scheduler.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}