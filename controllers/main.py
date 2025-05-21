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
            
            # Create an environment with superuser access to avoid permission issues
            env = request.env(su=True)
            
            # Ensure MCUBE API source exists
            mcube_source = env['utm.source'].search([('name', '=', 'MCUBE API')], limit=1)
            if not mcube_source:
                _logger.info("Creating new UTM source: MCUBE API")
                mcube_source = env['utm.source'].create({'name': 'MCUBE API'})
            
            # More thorough duplicate check - check phone number in multiple fields
            existing_lead = env['crm.lead'].search([
                '|', '|', '|',
                ('phone', '=', phone),
                ('mobile', '=', phone),
                ('partner_id.phone', '=', phone),
                ('partner_id.mobile', '=', phone)
            ], limit=1)
            
            # Create call record entry regardless of whether we have a lead or not
            call_record_vals = {
                'call_id': call_id,
                'phone_number': phone,
                'virtual_number': virtual_number,
                'recording_url': recording_url,
                'call_date': data.get('starttime', False),
                'duration': data.get('answeredtime', False),
                'direction': data.get('direction', 'inbound'),
                'status': data.get('dialstatus', False),
                'disconnected_by': data.get('disconnectedby', False),
                'agent_name': data.get('agentname', False),
            }
            
            if existing_lead:
                # Link call record to existing lead
                call_record_vals['lead_id'] = existing_lead.id
                
                # Create call record entry
                call_record = env['mcube.call.record'].create(call_record_vals)
                _logger.info(f"Created call record (ID: {call_record.id}) for existing lead (ID: {existing_lead.id})")
                
                response_data = {
                    "status": "success",
                    "message": "Call record added to existing lead",
                    "lead_id": existing_lead.id,
                    "call_record_id": call_record.id
                }
                return request.make_response(
                    json.dumps(response_data),
                    headers=[('Content-Type', 'application/json')],
                    status=200
                )
            
            # Find the user with matching MCUBE virtual number
            # Use env(su=True) to avoid access rights issues
            user = env['res.users'].search([('mcube_virtual_number', '=', virtual_number)], limit=1)
            
            if not user:
                _logger.warning(f"No user found with MCUBE virtual number: {virtual_number}")
                
                # Try alternative methods to find a responsible user
                # 1. Check if the phone number is from a known customer with a salesperson
                partner = env['res.partner'].search([('phone', '=', phone), ('user_id', '!=', False)], limit=1)
                if partner and partner.user_id:
                    user = partner.user_id
                    _logger.info(f"Assigned to user {user.name} based on existing customer relationship")
                else:
                    # 2. Try to assign to a default sales team member (round-robin)
                    sales_team = env['crm.team'].search([('use_leads', '=', True)], limit=1)
                    if sales_team:
                        # Get all active users in the sales team
                        team_members = sales_team.member_ids.filtered(lambda m: m.active)
                        if team_members:
                            # Simple round-robin: get the count of leads for each user and pick the one with fewest
                            member_lead_counts = []
                            for member in team_members:
                                lead_count = env['crm.lead'].search_count([('user_id', '=', member.id)])
                                member_lead_counts.append((member, lead_count))
                            
                            # Sort by lead count (ascending) and take the first one
                            user = sorted(member_lead_counts, key=lambda x: x[1])[0][0] if member_lead_counts else False
                            if user:
                                _logger.info(f"Assigned to sales team member {user.name} via round-robin")
                
                # If all else fails, assign to admin user
                if not user:
                    _logger.warning("No suitable user found, assigning to admin")
                    user = env.ref('base.user_admin')
            
            # Create new lead
            lead_vals = {
                'name': f"Inbound Call from {phone}",
                'phone': phone,
                'user_id': user.id if user else False,
                'team_id': user.sale_team_id.id if hasattr(user, 'sale_team_id') and user.sale_team_id else False,
                'type': 'lead',
                'source_id': mcube_source.id,  # Set the lead source to MCUBE API
            }
            
            try:
                new_lead = env['crm.lead'].create(lead_vals)
                
                # Link and create call record
                call_record_vals['lead_id'] = new_lead.id
                call_record = env['mcube.call.record'].create(call_record_vals)
                
                _logger.info(f"Created new lead (ID: {new_lead.id}) with call record (ID: {call_record.id})")
                
                response_data = {
                    "status": "success",
                    "message": "Lead created with call record",
                    "lead_id": new_lead.id,
                    "call_record_id": call_record.id
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
