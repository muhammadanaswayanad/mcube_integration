{
    'name': 'MCUBE CRM Integration',
    'version': '1.0',
    'summary': 'Integrate MCUBE call system with CRM leads',
    'description': """
        This module integrates MCUBE call system with Odoo CRM.
        It listens for inbound call webhooks from MCUBE and:
        - Creates new CRM leads for new phone numbers
        - Links leads to correct salesperson based on virtual number
        - Saves call recording URLs in leads
    """,
    'category': 'CRM',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': ['base', 'crm'],
    'data': [
        'views/res_users_views.xml',
        'views/mcube_call_record_views.xml',
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
