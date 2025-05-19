from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    call_recording_url = fields.Char(string="Call Recording URL",
                                    help="URL to the recorded call from MCUBE system")
