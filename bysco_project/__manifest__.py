# -*- coding: utf-8 -*-
{
    'name': "bysco项目管理",

    'summary': """bysco项目管理
        """,

    'description': """
    bysco项目管理
    """,

    'author': "bysco",
    'website': "http://www.bysco.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'BYSCO',
    'version': '0.1',

    # any module necessary for this one to work correctly

    'depends': ['project', 'hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/peoject_group.xml',
        'data/project_task.xml',
        'views/project_task_views.xml',
        'views/res_users_views.xml',
        'views/work_report_inquiry.xml',
        'views/technical_department_work_inquiries.xml',
        # 'views/purchase_order_views.xml',
    ],
    # only loaded in demonstration mode
    'qweb':[
        # 'static/src/xml/base.xml',
    ],
    'demo': [
        # 'demo/demo.xml',
    ],
}
