from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    call_recording_url = fields.Char(string="Call Recording URL",
                                    help="URL to the recorded call from MCUBE system")
    call_record_ids = fields.One2many('mcube.call.record', 'lead_id', string="Call Records")
    call_count = fields.Integer(string="Call Count", compute='_compute_call_count')
    
    def _compute_call_count(self):
        for lead in self:
            lead.call_count = len(lead.call_record_ids)
