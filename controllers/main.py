from odoo import http
from odoo.http import request
import logging
import json
import threading
from odoo.api import Environment
import odoo

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
            
            # Get necessary info for background processing
            db_name = request.env.cr.dbname
            
            # Process the webhook data in a background thread with proper context
            thread = threading.Thread(
                target=self._process_webhook_data,
                args=(db_name, data)
            )
            thread.start()
            
            # Return immediate response while processing continues in background
            return request.make_response(
                json.dumps({"status": "accepted", "message": "Request accepted for processing"}),
                headers=[('Content-Type', 'application/json')],
                status=202
            )
                
        except Exception as e:
            _logger.exception(f"Error processing MCUBE webhook: {str(e)}")
            return request.make_response(
                json.dumps({"status": "error", "message": str(e)}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    def _process_webhook_data(self, db_name, data):
        """Process webhook data in a separate thread to avoid timeout issues"""
        try:
            _logger.info("Starting background processing of webhook data")
            
            # Create a new registry and environment for the thread
            registry = odoo.registry(db_name)
            with registry.cursor() as cr:
                env = Environment(cr, odoo.SUPERUSER_ID, {})
                
                # Extract required fields
                phone = data.get('callto')
                virtual_number = data.get('clicktocalldid')
                recording_url = data.get('filename')
                call_id = data.get('callid')
                
                _logger.info(f"Background thread processing call ID {call_id} from {phone}")
                
                if not phone:
                    _logger.warning("Missing phone number in MCUBE webhook data")
                    return
                
                # Ensure MCUBE API source exists
                try:
                    _logger.info("Checking for MCUBE API source")
                    mcube_source = env['utm.source'].search([('name', '=', 'MCUBE API')], limit=1)
                    if not mcube_source:
                        _logger.info("Creating new UTM source: MCUBE API")
                        mcube_source = env['utm.source'].create({'name': 'MCUBE API'})
                    _logger.info(f"Using UTM source: {mcube_source.name} (ID: {mcube_source.id})")
                except Exception as source_error:
                    _logger.exception(f"Error with UTM source: {source_error}")
                    mcube_source = False
                
                # More thorough duplicate check with timeout handling
                try:
                    _logger.info(f"Searching for existing lead with phone: {phone}")
                    # Set a timeout for the search operation
                    existing_lead = env['crm.lead'].with_context(prefetch_fields=False).search([
                        '|', '|', '|',
                        ('phone', '=', phone),
                        ('mobile', '=', phone),
                        ('partner_id.phone', '=', phone),
                        ('partner_id.mobile', '=', phone)
                    ], limit=1)
                    _logger.info(f"Search complete. Existing lead found: {bool(existing_lead)}")
                    if existing_lead:
                        _logger.info(f"Found existing lead ID: {existing_lead.id}, Name: {existing_lead.name}")
                except Exception as search_error:
                    _logger.exception(f"Error searching for existing lead: {search_error}")
                    existing_lead = False
                
                # Create call record entry regardless of whether we have a lead or not
                _logger.info("Preparing call record values")
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
                    
                    try:
                        _logger.info(f"Creating call record for existing lead ID: {existing_lead.id}")
                        # Create call record entry
                        call_record = env['mcube.call.record'].create(call_record_vals)
                        _logger.info(f"Created call record (ID: {call_record.id}) for existing lead (ID: {existing_lead.id})")
                        
                        # Need to commit since we're in a separate thread
                        _logger.info("Committing transaction")
                        cr.commit()
                        return
                    except Exception as record_error:
                        _logger.exception(f"Error creating call record for existing lead: {record_error}")
                        cr.rollback()
                        # Continue to try creating a new lead
                
                # Find the user with matching MCUBE virtual number
                try:
                    _logger.info(f"Searching for user with virtual number: {virtual_number}")
                    user = env['res.users'].search([('mcube_virtual_number', '=', virtual_number)], limit=1)
                    
                    if user:
                        _logger.info(f"Found user with matching virtual number: {user.name} (ID: {user.id})")
                    else:
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
                        _logger.info(f"Assigned to admin user: {user.name} (ID: {user.id})")
                except Exception as user_error:
                    _logger.exception(f"Error finding responsible user: {user_error}")
                    user = False
                
                # Create new lead
                _logger.info("Preparing to create new lead")
                lead_vals = {
                    'name': f"Inbound Call from {phone}",
                    'phone': phone,
                    'user_id': user.id if user else False,
                    'team_id': user.sale_team_id.id if hasattr(user, 'sale_team_id') and user.sale_team_id else False,
                    'type': 'lead',
                }
                
                # Add source only if we successfully found/created one
                if mcube_source:
                    lead_vals['source_id'] = mcube_source.id
                
                # Check if the model has required fields we're not setting
                try:
                    _logger.info("Checking for required fields on crm.lead model")
                    lead_fields = env['crm.lead'].fields_get()
                    required_fields = []
                    for field_name, field_attrs in lead_fields.items():
                        if field_attrs.get('required') and field_name not in lead_vals:
                            required_fields.append(field_name)
                    
                    if required_fields:
                        _logger.warning(f"Missing required fields for lead creation: {', '.join(required_fields)}")
                        # Try to set default values for required fields
                        for field in required_fields:
                            lead_vals[field] = False  # Set a default value
                except Exception as fields_error:
                    _logger.exception(f"Error checking required fields: {fields_error}")
                
                try:
                    _logger.info(f"Creating new lead with values: {lead_vals}")
                    new_lead = env['crm.lead'].create(lead_vals)
                    _logger.info(f"Successfully created new lead (ID: {new_lead.id}, Name: {new_lead.name})")
                    
                    # Link and create call record
                    call_record_vals['lead_id'] = new_lead.id
                    _logger.info("Creating call record linked to new lead")
                    call_record = env['mcube.call.record'].create(call_record_vals)
                    _logger.info(f"Created call record (ID: {call_record.id})")
                    
                    # Need to commit since we're in a separate thread
                    _logger.info("Committing transaction")
                    cr.commit()
                    _logger.info("Background processing completed successfully")
                except Exception as create_error:
                    _logger.exception(f"Error creating lead: {create_error}")
                    # Rollback in case of error
                    _logger.info("Rolling back transaction due to error")
                    cr.rollback()
                    
        except Exception as process_error:
            _logger.exception(f"Critical error in background processing of webhook data: {process_error}")
