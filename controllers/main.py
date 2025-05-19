from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class MCubeWebhookController(http.Controller):
    
    @http.route('/mcube/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def mcube_webhook(self, **kw):
        try:
            # Get the JSON data from the request
            data = request.jsonrequest
            
            # Extract required fields
            callto = data.get('callto')  # Customer phone number
            clicktocalldid = data.get('clicktocalldid')  # Salesperson's virtual number
            filename = data.get('filename')  # Call recording URL
            call_id = data.get('callid')  # Unique call ID
            
            # Log the incoming webhook data
            _logger.info(f"MCUBE Webhook received: Call ID {call_id} from {callto} to virtual number {clicktocalldid}")
            
            if not all([callto, clicktocalldid]):
                _logger.warning("Missing required fields in MCUBE webhook data")
                return {'status': 'error', 'message': 'Missing required fields'}
                
            # Use sudo() as this is a public endpoint with no authentication
            env = request.env
            
            # Check if a lead already exists with this phone number
            existing_lead = env['crm.lead'].sudo().search([('phone', '=', callto)], limit=1)
            
            if not existing_lead:
                # Find the user with matching MCUBE virtual number
                user = env['res.users'].sudo().search([('mcube_virtual_number', '=', clicktocalldid)], limit=1)
                
                if not user:
                    _logger.warning(f"No user found with MCUBE virtual number: {clicktocalldid}")
                    # Create lead with admin user if no matching salesperson found
                    user = env.ref('base.user_admin')
                
                # Create new lead
                lead_vals = {
                    'name': f"Inbound Call from {callto}",
                    'phone': callto,
                    'user_id': user.id,
                    'team_id': user.sale_team_id.id if user.sale_team_id else None,
                    'type': 'lead',
                    'call_recording_url': filename,
                    'description': f"""
                        Inbound call received on {data.get('starttime')}
                        Call duration: {data.get('answeredtime')}
                        Call recording: {filename}
                        Direction: {data.get('direction')}
                        Call status: {data.get('dialstatus')}
                        Disconnected by: {data.get('disconnectedby')}
                    """
                }
                
                new_lead = env['crm.lead'].sudo().create(lead_vals)
                _logger.info(f"Created new lead (ID: {new_lead.id}) for phone: {callto}")
                return {'status': 'success', 'message': 'Lead created', 'lead_id': new_lead.id}
            else:
                # Update existing lead with call recording info
                existing_lead.sudo().write({
                    'call_recording_url': filename,
                    'description': existing_lead.description + f"\n\nCall recording from {data.get('starttime')}: {filename}"
                })
                _logger.info(f"Updated existing lead (ID: {existing_lead.id}) with new call recording")
                return {'status': 'success', 'message': 'Lead updated', 'lead_id': existing_lead.id}
                
        except Exception as e:
            _logger.exception("Error processing MCUBE webhook")
            return {'status': 'error', 'message': str(e)}
