from odoo import models, fields, api, _
import json
import logging

_logger = logging.getLogger(__name__)


class TwitterApiResponse(models.Model):
    _name = 'twitter.api.response'
    _description = 'Twitter API Response Log'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    service_id = fields.Many2one(
        'twitter.service',
        string='Service',
        required=True,
        ondelete='cascade'
    )
    
    account_id = fields.Many2one(
        'twitter.account',
        string='Account',
        related='service_id.account_id',
        store=True
    )
    
    # Request Info
    request_type = fields.Selection([
        ('post_tweet', 'Post Tweet'),
        ('get_timeline', 'Get Timeline'),
        ('upload_media', 'Upload Media'),
        ('get_user_info', 'Get User Info'),
        ('auth', 'Authentication'),
        ('other', 'Other')
    ], string='Request Type', required=True)
    
    endpoint = fields.Char(
        string='API Endpoint',
        help='Twitter API endpoint called'
    )
    
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE')
    ], string='HTTP Method')
    
    # Response Info
    success = fields.Boolean(
        string='Success',
        help='Whether the API call was successful'
    )
    
    status_code = fields.Integer(
        string='HTTP Status Code'
    )
    
    response_time_ms = fields.Integer(
        string='Response Time (ms)',
        help='Time taken for API response in milliseconds'
    )
    
    # Data
    request_data = fields.Text(
        string='Request Data',
        help='JSON data sent in the request'
    )
    
    response_data = fields.Text(
        string='Response Data',
        help='JSON response from Twitter API'
    )
    
    error_type = fields.Selection([
        ('validation_error', 'Validation Error'),
        ('auth_error', 'Authentication Error'),
        ('rate_limit_error', 'Rate Limit Error'),
        ('api_error', 'API Error'),
        ('network_error', 'Network Error'),
        ('system_error', 'System Error'),
        ('not_implemented', 'Not Implemented')
    ], string='Error Type')
    
    error_message = fields.Text(
        string='Error Message'
    )
    
    # Rate Limiting
    rate_limit_remaining = fields.Integer(
        string='Rate Limit Remaining',
        help='Remaining API calls after this request'
    )
    
    rate_limit_reset = fields.Datetime(
        string='Rate Limit Reset',
        help='When rate limit resets'
    )
    
    # Additional metadata
    tweet_id = fields.Char(
        string='Tweet ID',
        help='ID of tweet if this was a post operation'
    )
    
    media_id = fields.Char(
        string='Media ID',
        help='ID of uploaded media if this was a media upload'
    )
    
    timeline_count = fields.Integer(
        string='Timeline Count',
        help='Number of tweets retrieved if this was a timeline request'
    )
    
    @api.depends('request_type', 'success', 'create_date')
    def _compute_display_name(self):
        for record in self:
            status = "✓" if record.success else "✗"
            timestamp = record.create_date.strftime('%H:%M:%S') if record.create_date else ''
            record.display_name = f"{status} {record.request_type} - {timestamp}"
    
    @api.model
    def log_api_call(self, service_id, request_type, endpoint=None, method=None, 
                     request_data=None, response_data=None, success=True, 
                     status_code=None, response_time_ms=None, error_type=None, 
                     error_message=None, **kwargs):
        """
        Log an API call response
        
        Args:
            service_id (int): ID of the Twitter service
            request_type (str): Type of API request
            endpoint (str): API endpoint URL
            method (str): HTTP method
            request_data (dict): Request payload
            response_data (dict): Response data
            success (bool): Whether call was successful
            status_code (int): HTTP status code
            response_time_ms (int): Response time in milliseconds
            error_type (str): Type of error if failed
            error_message (str): Error message if failed
            **kwargs: Additional metadata (tweet_id, media_id, etc.)
        
        Returns:
            twitter.api.response: Created log record
        """
        values = {
            'service_id': service_id,
            'request_type': request_type,
            'endpoint': endpoint,
            'method': method,
            'success': success,
            'status_code': status_code,
            'response_time_ms': response_time_ms,
            'error_type': error_type,
            'error_message': error_message,
        }
        
        # Convert data to JSON strings
        if request_data:
            values['request_data'] = json.dumps(request_data, indent=2)
        
        if response_data:
            values['response_data'] = json.dumps(response_data, indent=2)
        
        # Add any additional metadata
        for key, value in kwargs.items():
            if hasattr(self, key):
                values[key] = value
        
        try:
            return self.create(values)
        except Exception as e:
            _logger.error(f"Failed to log API response: {str(e)}")
            return self.env['twitter.api.response']
    
    @api.model
    def get_success_rate(self, service_id=None, hours=24):
        """
        Calculate API success rate
        
        Args:
            service_id (int): Optional service ID to filter by
            hours (int): Number of hours to look back
            
        Returns:
            dict: Success rate statistics
        """
        domain = [
            ('create_date', '>=', fields.Datetime.now() - fields.timedelta(hours=hours))
        ]
        
        if service_id:
            domain.append(('service_id', '=', service_id))
        
        records = self.search(domain)
        
        if not records:
            return {
                'total_calls': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'success_rate': 0.0,
                'error_breakdown': {}
            }
        
        total_calls = len(records)
        successful_calls = len(records.filtered('success'))
        failed_calls = total_calls - successful_calls
        success_rate = (successful_calls / total_calls) * 100 if total_calls > 0 else 0
        
        # Error breakdown
        error_breakdown = {}
        failed_records = records.filtered(lambda r: not r.success)
        for error_type in failed_records.mapped('error_type'):
            if error_type:
                error_count = len(failed_records.filtered(lambda r: r.error_type == error_type))
                error_breakdown[error_type] = error_count
        
        return {
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'failed_calls': failed_calls,
            'success_rate': round(success_rate, 2),
            'error_breakdown': error_breakdown
        }
    
    @api.model
    def get_rate_limit_usage(self, service_id=None, hours=1):
        """
        Get rate limit usage statistics
        
        Args:
            service_id (int): Optional service ID to filter by
            hours (int): Number of hours to look back
            
        Returns:
            dict: Rate limit usage data
        """
        domain = [
            ('create_date', '>=', fields.Datetime.now() - fields.timedelta(hours=hours))
        ]
        
        if service_id:
            domain.append(('service_id', '=', service_id))
        
        records = self.search(domain, order='create_date desc')
        
        if not records:
            return {
                'calls_in_period': 0,
                'current_remaining': None,
                'rate_limit_hits': 0
            }
        
        calls_in_period = len(records)
        rate_limit_hits = len(records.filtered(lambda r: r.error_type == 'rate_limit_error'))
        
        # Get most recent rate limit info
        latest_record = records[0] if records else None
        current_remaining = latest_record.rate_limit_remaining if latest_record else None
        
        return {
            'calls_in_period': calls_in_period,
            'current_remaining': current_remaining,
            'rate_limit_hits': rate_limit_hits
        }
    
    def action_view_request_data(self):
        """Action to view request data in a popup"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request Data'),
            'res_model': 'twitter.api.response',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('twitter_api_service.view_twitter_api_response_form_popup').id,
            'target': 'new',
            'context': {'show_request_data': True}
        }
    
    def action_view_response_data(self):
        """Action to view response data in a popup"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Response Data'),
            'res_model': 'twitter.api.response',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('twitter_api_service.view_twitter_api_response_form_popup').id,
            'target': 'new',
            'context': {'show_response_data': True}
        }