from odoo import http, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class TwitterOAuthController(http.Controller):

    @http.route('/twitter/oauth/callback', type='http', auth='user', methods=['GET'])
    def oauth_callback(self, **kwargs):
        """Handle OAuth callback from Twitter"""
        
        code = kwargs.get('code')
        state = kwargs.get('state')
        error = kwargs.get('error')
        
        if error:
            _logger.error(f"Twitter OAuth error: {error}")
            return request.render('twitter_api_service.oauth_error', {
                'error': error,
                'error_description': kwargs.get('error_description', 'Unknown error')
            })
        
        if not code or not state:
            _logger.error("Missing code or state in OAuth callback")
            return request.render('twitter_api_service.oauth_error', {
                'error': 'invalid_request',
                'error_description': 'Missing authorization code or state parameter'
            })
        
        try:
            # Find the Twitter account by state
            account = request.env['twitter.account'].sudo().search([
                ('state', '=', state)
            ], limit=1)
            
            if not account:
                _logger.error(f"No Twitter account found for state: {state}")
                return request.render('twitter_api_service.oauth_error', {
                    'error': 'invalid_state',
                    'error_description': 'Invalid state parameter'
                })
            
            # Complete authentication
            success = account.complete_authentication(code, state)
            
            if success:
                # Clear the state
                account.write({'state': False})
                
                return request.render('twitter_api_service.oauth_success', {
                    'account_name': account.name,
                    'twitter_username': account.twitter_username
                })
            else:
                return request.render('twitter_api_service.oauth_error', {
                    'error': 'auth_failed',
                    'error_description': 'Failed to complete authentication'
                })
                
        except Exception as e:
            _logger.error(f"OAuth callback error: {str(e)}")
            return request.render('twitter_api_service.oauth_error', {
                'error': 'system_error',
                'error_description': str(e)
            })

    @http.route('/twitter/api/test', type='json', auth='user', methods=['POST'])
    def test_api(self, service_id):
        """Test API endpoint for AJAX calls"""
        
        try:
            service = request.env['twitter.service'].browse(service_id)
            
            if not service.exists():
                return {'success': False, 'error': 'Service not found'}
            
            # Test connection
            result = service.account_id.test_connection()
            
            return {
                'success': True,
                'authenticated': service.account_id.is_authenticated,
                'username': service.account_id.twitter_username,
                'rate_limit_remaining': service.account_id.rate_limit_remaining
            }
            
        except Exception as e:
            _logger.error(f"API test error: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/twitter/api/post_tweet', type='json', auth='user', methods=['POST'])
    def post_tweet_api(self, service_id, text, reply_to_tweet_id=None):
        """API endpoint to post tweets via AJAX"""
        
        try:
            service = request.env['twitter.service'].browse(service_id)
            
            if not service.exists():
                return {'success': False, 'error': 'Service not found'}
            
            # Post tweet
            result = service.post_tweet(text, reply_to_tweet_id=reply_to_tweet_id)
            
            # Log the API call
            request.env['twitter.api.response'].sudo().log_api_call(
                service_id=service.id,
                request_type='post_tweet',
                endpoint='https://api.twitter.com/2/tweets',
                method='POST',
                request_data={'text': text, 'reply_to_tweet_id': reply_to_tweet_id},
                response_data=result,
                success=result.get('success', False),
                error_type=result.get('error'),
                error_message=result.get('message') if not result.get('success') else None,
                tweet_id=result.get('data', {}).get('tweet_id')
            )
            
            return result
            
        except Exception as e:
            _logger.error(f"Post tweet API error: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/twitter/api/get_timeline', type='json', auth='user', methods=['POST'])
    def get_timeline_api(self, service_id, max_results=10, exclude_replies=True, exclude_retweets=True):
        """API endpoint to get timeline via AJAX"""
        
        try:
            service = request.env['twitter.service'].browse(service_id)
            
            if not service.exists():
                return {'success': False, 'error': 'Service not found'}
            
            # Get timeline
            result = service.get_user_timeline(
                max_results=max_results,
                exclude_replies=exclude_replies,
                exclude_retweets=exclude_retweets
            )
            
            # Log the API call
            request.env['twitter.api.response'].sudo().log_api_call(
                service_id=service.id,
                request_type='get_timeline',
                endpoint=f'https://api.twitter.com/2/users/{service.account_id.twitter_user_id}/tweets',
                method='GET',
                request_data={
                    'max_results': max_results,
                    'exclude_replies': exclude_replies,
                    'exclude_retweets': exclude_retweets
                },
                response_data=result,
                success=result.get('success', False),
                error_type=result.get('error'),
                error_message=result.get('message') if not result.get('success') else None,
                timeline_count=len(result.get('data', {}).get('tweets', []))
            )
            
            return result
            
        except Exception as e:
            _logger.error(f"Get timeline API error: {str(e)}")
            return {'success': False, 'error': str(e)}