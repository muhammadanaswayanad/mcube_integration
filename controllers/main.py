from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)

class MCubeWebhookController(http.Controller):
    
    @http.route('/mcube/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def mcube_inbound_call(self, **kwargs):
        try:
            # Log raw request data for debugging
            raw_data = request.httprequest.data
            _logger.info(f"MCUBE Webhook RAW DATA: {raw_data}")
            
            try:
                data = json.loads(raw_data)
                _logger.info(f"MCUBE Webhook JSON: {data}")
            except json.JSONDecodeError as je:
                _logger.error(f"Failed to parse JSON: {je}")
                return request.make_response(
                    json.dumps({"status": "error", "message": "Invalid JSON data"}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            # Extract required fields
            phone = data.get('callto')
            virtual_number = data.get('clicktocalldid')
            recording_url = data.get('filename')
            call_id = data.get('callid')
            
            # Log the incoming webhook data
            _logger.info(f"MCUBE Webhook received: Call ID {call_id} from {phone} to virtual number {virtual_number}")
            
            if not phone:
                _logger.warning("Missing phone number in MCUBE webhook data")
                return request.make_response(
                    json.dumps({"status": "error", "message": "Missing phone number"}),
                    headers=[('Content-Type', 'application/json')],
                    status=400
                )
            
            # Check if a lead already exists with this phone number
            existing_lead = request.env['crm.lead'].sudo().search([('phone', '=', phone)], limit=1)
            
            if existing_lead:
                # Update existing lead with call recording info
                try:
                    # Check if call_recording_url field exists
                    if hasattr(existing_lead, 'call_recording_url'):
                        existing_lead.sudo().write({
                            'call_recording_url': recording_url,
                            'description': (existing_lead.description or '') + f"\n\nCall recording from {data.get('starttime', 'unknown time')}: {recording_url}"
                        })
                    else:
                        existing_lead.sudo().write({
                            'description': (existing_lead.description or '') + f"\n\nCall recording from {data.get('starttime', 'unknown time')}: {recording_url}"
                        })
                    
                    _logger.info(f"Updated existing lead (ID: {existing_lead.id}) with new call recording")
                    response_data = {
                        "status": "success",
                        "message": "Lead updated",
                        "lead_id": existing_lead.id
                    }
                except Exception as write_error:
                    _logger.exception(f"Error updating lead: {write_error}")
                    response_data = {
                        "status": "error", 
                        "message": f"Error updating lead: {str(write_error)}"
                    }
                
                return request.make_response(
                    json.dumps(response_data),
                    headers=[('Content-Type', 'application/json')],
                    status=200
                )
            
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
                'team_id': user.sale_team_id.id if hasattr(user, 'sale_team_id') and user.sale_team_id else False,
                'type': 'lead',
                'description': f"""
                    Inbound call received
                    Call ID: {call_id}
                    Call recording: {recording_url}
                    Direction: {data.get('direction', 'unknown')}
                    Call status: {data.get('dialstatus', 'unknown')}
                    Agent name: {data.get('agentname', 'unknown')}
                """
            }
            
            # Check if call_recording_url field exists in crm.lead model
            if 'call_recording_url' in request.env['crm.lead']._fields:
                lead_vals['call_recording_url'] = recording_url
            
            try:
                new_lead = request.env['crm.lead'].sudo().create(lead_vals)
                _logger.info(f"Created new lead (ID: {new_lead.id}) for phone: {phone}")
                
                response_data = {
                    "status": "success",
                    "message": "Lead created successfully",
                    "lead_id": new_lead.id
                }
                return request.make_response(
                    json.dumps(response_data),
                    headers=[('Content-Type', 'application/json')],
                    status=201
                )
            except Exception as create_error:
                _logger.exception(f"Error creating lead: {create_error}")
                return request.make_response(
                    json.dumps({"status": "error", "message": f"Error creating lead: {str(create_error)}"}),
                    headers=[('Content-Type', 'application/json')],
                    status=500
                )
                
        except Exception as e:
            _logger.exception(f"Error processing MCUBE webhook: {str(e)}")
            return request.make_response(
                json.dumps({"status": "error", "message": str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
