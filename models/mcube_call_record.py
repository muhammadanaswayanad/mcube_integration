from odoo import fields, models, api

class MCubeCallRecord(models.Model):
    _name = "mcube.call.record"
    _description = "MCUBE Call Record"
    _rec_name = "call_id"
    _order = "call_date desc"
    
    call_id = fields.Char("Call ID", required=True, index=True)
    lead_id = fields.Many2one('crm.lead', string="Related Lead", ondelete='cascade', index=True)
    phone_number = fields.Char("Phone Number", index=True)
    virtual_number = fields.Char("Virtual Number")
    recording_url = fields.Char("Recording URL")
    call_date = fields.Datetime("Call Date")
    duration = fields.Float("Duration (seconds)")
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], string="Direction", default='inbound')
    status = fields.Char("Call Status")
    disconnected_by = fields.Char("Disconnected By")
    agent_name = fields.Char("Agent Name")
    has_recording = fields.Boolean(compute="_compute_has_recording", store=True)
    
    @api.depends('recording_url')
    def _compute_has_recording(self):
        for record in self:
            record.has_recording = bool(record.recording_url)
    
    def open_recording_url(self):
        """Action to open the recording URL in a new browser tab"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.recording_url,
            'target': 'new',
        }
