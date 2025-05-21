from odoo import fields, models

class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    call_record_ids = fields.One2many('mcube.call.record', 'lead_id', string="Call Records")
    call_count = fields.Integer(string="Call Count", compute='_compute_call_count')
    
    def _compute_call_count(self):
        for lead in self:
            lead.call_count = len(lead.call_record_ids)
