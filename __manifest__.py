{
    'name': 'MCUBE Integration',
    'version': '1.0',
    'category': 'CRM',
    'summary': 'Integration with MCUBE call tracking system',
    'description': """
        This module integrates Odoo with MCUBE call tracking system to:
        - Create leads from inbound calls
        - Track call recordings
        - Link calls to users via virtual numbers
    """,
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': [
        'base',
        'crm',
    ],
    'data': [
        'views/res_users_views.xml',
        'views/mcube_call_record_views.xml',
        'views/crm_lead_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
