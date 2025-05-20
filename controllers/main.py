from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)

class MCubeWebhookController(http.Controller):
    
    @http.route('/mcube/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def mcube_inbound_call(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            
            # Extract required fields
            phone = data.get('callto')
            virtual_number = data.get('clicktocalldid')
            recording_url = data.get('filename')
            call_id = data.get('callid')
            
            # Log the incoming webhook data
            _logger.info(f"MCUBE Webhook received: Call ID {call_id} from {phone} to virtual number {virtual_number}")
            
            if not phone:
                _logger.warning("Missing phone number in MCUBE webhook data")
                return request.make_response(json.dumps({
                    "status": "error",
                    "message": "Missing phone number"
                }), headers=[('Content-Type', 'application/json')])
            
            # Check if a lead already exists with this phone number
            existing_lead = request.env['crm.lead'].sudo().search([('phone', '=', phone)], limit=1)
            
            if existing_lead:
                # Update existing lead with call recording info
                existing_lead.sudo().write({
                    'call_recording_url': recording_url,
                    'description': existing_lead.description + f"\n\nCall recording from {data.get('starttime')}: {recording_url}"
                })
                _logger.info(f"Updated existing lead (ID: {existing_lead.id}) with new call recording")
                return request.make_response(json.dumps({
                    "status": "exists",
                    "message": "Lead updated",
                    "lead_id": existing_lead.id
                }), headers=[('Content-Type', 'application/json')])
            
            # Find the user with matching MCUBE virtual number
            user = request.env['res.users'].sudo().search([('mcube_virtual_number', '=', virtual_number)], limit=1)
            
            if not user:
                _logger.warning(f"No user found with MCUBE virtual number: {virtual_number}")
                # Create lead with admin user if no matching salesperson found
                user = request.env.ref('base.user_admin')
            
            # Create new lead
            lead_vals = {
                'name': f"Inbound Call from {phone}",
                'phone': phone,
                'user_id': user.id,
                'team_id': user.sale_team_id.id if user.sale_team_id else None,
                'type': 'lead',
                'call_recording_url': recording_url,
                'description': f"""
                    Inbound call received on {data.get('starttime')}
                    Call duration: {data.get('answeredtime')}
                    Call recording: {recording_url}
                    Direction: {data.get('direction')}
                    Call status: {data.get('dialstatus')}
                    Disconnected by: {data.get('disconnectedby')}
                """
            }
            
            new_lead = request.env['crm.lead'].sudo().create(lead_vals)
            _logger.info(f"Created new lead (ID: {new_lead.id}) for phone: {phone}")
            
            return request.make_response(json.dumps({
                "status": "created",
                "message": "Lead created",
                "lead_id": new_lead.id
            }), headers=[('Content-Type', 'application/json')])
                
        except Exception as e:
            _logger.exception("Error processing MCUBE webhook")
            return request.make_response(json.dumps({
                "status": "error",
                "message": str(e)
            }), headers=[('Content-Type', 'application/json')])
