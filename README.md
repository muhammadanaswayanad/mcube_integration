# MCUBE Integration Addon

## Overview

The MCUBE Integration addon connects Odoo CRM with the MCUBE call tracking system to automatically create leads from inbound calls, track call recordings, and manage user-specific virtual phone numbers.

## Architecture

### Core Components

1. **Webhook Controller** (`controllers/main.py`)
   - Receives POST requests from MCUBE system
   - Processes call data in background threads
   - Creates leads and call records automatically

2. **Models**
   - `mcube.call.record`: Stores call information and recordings
   - `res.users` (extended): Adds MCUBE virtual number field
   - `crm.lead` (extended): Links to call records

3. **Views**
   - User configuration for virtual numbers
   - Call record management interface
   - Lead integration with call history

## File Structure

```
mcube_integration/
├── __init__.py                 # Module initialization
├── __manifest__.py            # Module manifest and dependencies
├── README.md                  # This documentation
├── controllers/
│   ├── __init__.py
│   └── main.py               # Webhook endpoint controller
├── models/
│   ├── __init__.py
│   ├── crm_lead.py          # CRM Lead extensions
│   ├── mcube_call_record.py # Call record model
│   └── res_users.py         # User extensions
├── security/
│   └── ir.model.access.csv  # Access control rules
└── views/
    ├── crm_lead_views.xml    # Lead form modifications
    ├── mcube_call_record_views.xml # Call record views
    └── res_users_views.xml   # User form modifications
```

## Data Flow

### Inbound Call Processing

1. **MCUBE System** → Webhook (`/mcube/webhook`)
2. **Webhook** → Background Thread Processing
3. **Lead Search** → Check for existing lead by phone number
4. **User Assignment** → Match virtual number to user
5. **Record Creation** → Create call record (and lead if needed)

### Expected Webhook Payload

```json
{
    "callto": "customer_phone_number",
    "clicktocalldid": "virtual_number",
    "filename": "recording_url",
    "callid": "unique_call_id",
    "starttime": "2023-01-01 12:00:00",
    "answeredtime": 120,
    "direction": "inbound",
    "dialstatus": "ANSWERED",
    "disconnectedby": "customer",
    "agentname": "agent_name"
}
```

## Configuration

### User Setup

1. Navigate to **Settings → Users & Companies → Users**
2. Edit user profile
3. Go to **Preferences** tab
4. Set **MCUBE Virtual Number** field

### Security

Access rights are configured for:
- `base.group_user`: Full access to call records
- `base.group_portal`: Read-only access
- `base.group_public`: Read-only access

## Database Schema

### mcube.call.record

| Field | Type | Description |
|-------|------|-------------|
| call_id | Char | Unique call identifier from MCUBE |
| lead_id | Many2one | Related CRM lead |
| phone_number | Char | Customer phone number |
| virtual_number | Char | Agent's virtual number |
| recording_url | Char | URL to call recording |
| call_date | Datetime | When call occurred |
| duration | Float | Call duration in seconds |
| direction | Selection | inbound/outbound |
| status | Char | Call status from MCUBE |
| disconnected_by | Char | Who ended the call |
| agent_name | Char | Agent handling the call |
| has_recording | Boolean | Computed field for recording availability |

## API Integration

### Webhook Endpoint

- **URL**: `/mcube/webhook`
- **Method**: POST
- **Auth**: Public (no authentication required)
- **Content-Type**: application/json

### Response Codes

- `202`: Request accepted for background processing
- `400`: Invalid JSON or missing required data
- `500`: Server error during processing

## Scaling Considerations

### Performance Optimization

1. **Background Processing**: Webhook uses threading to avoid timeouts
2. **Database Indexing**: Key fields (call_id, phone_number, lead_id) are indexed
3. **Efficient Queries**: Uses `with_context(prefetch_fields=False)` for large searches

### Horizontal Scaling

1. **Multiple Instances**: Webhook controller is stateless
2. **Database Partitioning**: Consider partitioning call_record table by date
3. **Caching**: Implement Redis caching for frequent user lookups

### Monitoring

Add logging for:
- Webhook request volume
- Processing times
- Failed lead creations
- Database query performance

## Future Enhancements

### High Priority

1. **Outbound Call Integration**
   - Click-to-call from Odoo
   - Automatic call logging
   - Call disposition tracking

2. **Advanced User Assignment**
   - Team-based round-robin
   - Skill-based routing
   - Load balancing algorithms

3. **Call Analytics**
   - Call volume dashboards
   - Performance metrics
   - Conversion tracking

### Medium Priority

1. **Integration Improvements**
   - Bulk webhook processing
   - Retry mechanisms for failed requests
   - Webhook authentication

2. **User Experience**
   - In-app call notifications
   - Call recording player widget
   - Mobile app support

### Low Priority

1. **Advanced Features**
   - AI call transcription
   - Sentiment analysis
   - Automatic lead scoring

## AI Assistant Guidelines

### Code Maintenance

When modifying this codebase, consider:

1. **Thread Safety**: Webhook processing uses background threads
2. **Database Transactions**: Always use proper commit/rollback
3. **Error Handling**: Extensive logging for debugging
4. **Performance**: Avoid N+1 queries in lead searches

### Common Modifications

1. **Adding New Webhook Fields**
   - Update `_process_webhook_data` method
   - Add corresponding model fields
   - Update view definitions

2. **Extending User Assignment Logic**
   - Modify user search in webhook controller
   - Consider team hierarchies and workload distribution

3. **Adding New Call Record Fields**
   - Update model definition
   - Add to tree/form views
   - Update security access if needed

### Testing Strategy

1. **Webhook Testing**
   - Use curl/Postman to simulate MCUBE requests
   - Test with malformed JSON
   - Verify background processing

2. **Lead Creation Testing**
   - Test with existing vs new customers
   - Verify user assignment logic
   - Check duplicate prevention

3. **UI Testing**
   - Verify call record displays
   - Test recording URL opening
   - Check user preference settings

## Dependencies

### Odoo Modules
- `base`: Core Odoo functionality
- `crm`: Customer Relationship Management

### Python Packages
- Standard library only (threading, json, logging)

## Troubleshooting

### Common Issues

1. **Webhook Timeouts**
   - Check background thread processing
   - Verify database connection stability
   - Monitor server resources

2. **Lead Creation Failures**
   - Check required field validation
   - Verify user permissions
   - Review database constraints

3. **User Assignment Issues**
   - Validate virtual number configuration
   - Check sales team setup
   - Verify fallback logic

### Debug Mode

Enable debug logging in Odoo configuration:
```ini
log_level = debug
log_handler = :DEBUG
```

Look for logs prefixed with `MCUBE Webhook` for detailed processing information.

## Version History

- **v1.0**: Initial release with basic webhook integration
- Future versions will be documented here

## Support

For technical issues or enhancement requests, refer to the module's git repository or contact the development team.
