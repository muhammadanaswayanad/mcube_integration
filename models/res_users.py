from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    mcube_virtual_number = fields.Char(string="MCUBE Virtual Number",
                                       help="Virtual phone number assigned to this user in the MCUBE system")
