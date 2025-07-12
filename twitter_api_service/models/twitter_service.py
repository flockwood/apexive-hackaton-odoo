from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class TwitterService(models.Model):
    _name = 'twitter.service'
    _description = 'Twitter API Service'
    _rec_name = 'name'

    name = fields.Char(
        string='Service Name',
        required=True,
        default='Twitter API Service'
    )
    
    account_id = fields.Many2one(
        'twitter.account',
        string='Twitter Account',
        required=True,
        help='Twitter account to use for API calls'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    # Statistics
    total_tweets_posted = fields.Integer(
        string='Total Tweets Posted',
        default=0,
        help='Total number of tweets posted through this service'
    )
    
    last_tweet_time = fields.Datetime(
        string='Last Tweet Time',
        help='When the last tweet was posted'
    )
    
    # Temporary field for tweet composition in form view
    tweet_text = fields.Text(
        string='Tweet Text',
        help='Temporary field for composing tweets in the form view'
    )
    
    def post_tweet(self, text, media_ids=None, reply_to_tweet_id=None):
        """
        Post a tweet immediately
        
        Args:
            text (str): Tweet text content (max 280 characters)
            media_ids (list): List of media IDs to attach
            reply_to_tweet_id (str): ID of tweet to reply to
            
        Returns:
            dict: Standardized response format
        """
        self.ensure_one()
        
        # Validate input
        if not text or not text.strip():
            return self._create_error_response(
                'validation_error',
                'Tweet text cannot be empty'
            )
        
        if len(text) > 280:
            return self._create_error_response(
                'validation_error',
                f'Tweet text too long: {len(text)}/280 characters'
            )
        
        # Check authentication
        if not self.account_id.is_authenticated:
            return self._create_error_response(
                'auth_error',
                'Twitter account is not authenticated'
            )
        
        # Check rate limits
        rate_limit_check = self._check_rate_limits('tweets')
        if not rate_limit_check['allowed']:
            return self._create_error_response(
                'rate_limit_error',
                rate_limit_check['message']
            )
        
        try:
            # Prepare tweet data
            tweet_data = {
                'text': text.strip()
            }
            
            # Add media if provided
            if media_ids:
                tweet_data['media'] = {'media_ids': media_ids}
            
            # Add reply reference if provided
            if reply_to_tweet_id:
                tweet_data['reply'] = {'in_reply_to_tweet_id': reply_to_tweet_id}
            
            # Make API request
            response = self.account_id._make_api_request(
                'POST',
                'https://api.twitter.com/2/tweets',
                data=tweet_data
            )
            
            if response.get('success'):
                # Update statistics
                self.write({
                    'total_tweets_posted': self.total_tweets_posted + 1,
                    'last_tweet_time': fields.Datetime.now()
                })
                
                # Log successful post
                tweet_id = response['data']['data']['id']
                _logger.info(f"Tweet posted successfully: {tweet_id}")
                
                return self._create_success_response(
                    data={
                        'tweet_id': tweet_id,
                        'text': text,
                        'posted_at': fields.Datetime.now().isoformat()
                    },
                    message='Tweet posted successfully'
                )
            else:
                return self._create_error_response(
                    response.get('error', 'api_error'),
                    response.get('message', 'Failed to post tweet')
                )
                
        except Exception as e:
            _logger.error(f"Error posting tweet: {str(e)}")
            return self._create_error_response(
                'system_error',
                f'System error: {str(e)}'
            )
    
    def get_user_timeline(self, max_results=10, exclude_replies=True, exclude_retweets=True):
        """
        Retrieve user timeline tweets
        
        Args:
            max_results (int): Number of tweets to retrieve (5-100)
            exclude_replies (bool): Whether to exclude replies
            exclude_retweets (bool): Whether to exclude retweets
            
        Returns:
            dict: Standardized response format with timeline data
        """
        self.ensure_one()
        
        # Validate parameters
        if max_results < 5 or max_results > 100:
            return self._create_error_response(
                'validation_error',
                'max_results must be between 5 and 100'
            )
        
        # Check authentication
        if not self.account_id.is_authenticated:
            return self._create_error_response(
                'auth_error',
                'Twitter account is not authenticated'
            )
        
        # Check rate limits
        rate_limit_check = self._check_rate_limits('timeline')
        if not rate_limit_check['allowed']:
            return self._create_error_response(
                'rate_limit_error',
                rate_limit_check['message']
            )
        
        try:
            # Prepare request parameters
            params = {
                'max_results': max_results,
                'tweet.fields': 'id,text,created_at,author_id,public_metrics,referenced_tweets',
                'user.fields': 'id,username,name,profile_image_url',
                'expansions': 'author_id,referenced_tweets.id'
            }
            
            # Add exclusions
            exclusions = []
            if exclude_replies:
                exclusions.append('replies')
            if exclude_retweets:
                exclusions.append('retweets')
            
            if exclusions:
                params['exclude'] = ','.join(exclusions)
            
            # Make API request
            user_id = self.account_id.twitter_user_id
            if not user_id:
                return self._create_error_response(
                    'config_error',
                    'Twitter user ID not found. Please re-authenticate.'
                )
            
            response = self.account_id._make_api_request(
                'GET',
                f'https://api.twitter.com/2/users/{user_id}/tweets',
                params=params
            )
            
            if response.get('success'):
                # Process timeline data
                timeline_data = self._process_timeline_response(response['data'])
                
                return self._create_success_response(
                    data=timeline_data,
                    message=f'Retrieved {len(timeline_data.get("tweets", []))} tweets'
                )
            else:
                return self._create_error_response(
                    response.get('error', 'api_error'),
                    response.get('message', 'Failed to retrieve timeline')
                )
                
        except Exception as e:
            _logger.error(f"Error retrieving timeline: {str(e)}")
            return self._create_error_response(
                'system_error',
                f'System error: {str(e)}'
            )
    
    def _process_timeline_response(self, api_response):
        """Process raw timeline response into standardized format"""
        processed_data = {
            'tweets': [],
            'users': {},
            'meta': api_response.get('meta', {})
        }
        
        # Process users data
        if 'includes' in api_response and 'users' in api_response['includes']:
            for user in api_response['includes']['users']:
                processed_data['users'][user['id']] = {
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'profile_image_url': user.get('profile_image_url')
                }
        
        # Process tweets data
        if 'data' in api_response:
            for tweet in api_response['data']:
                processed_tweet = {
                    'id': tweet['id'],
                    'text': tweet['text'],
                    'created_at': tweet['created_at'],
                    'author_id': tweet['author_id'],
                    'public_metrics': tweet.get('public_metrics', {}),
                    'is_reply': False,
                    'is_retweet': False,
                    'referenced_tweets': []
                }
                
                # Check for referenced tweets
                if 'referenced_tweets' in tweet:
                    for ref_tweet in tweet['referenced_tweets']:
                        processed_tweet['referenced_tweets'].append({
                            'type': ref_tweet['type'],
                            'id': ref_tweet['id']
                        })
                        
                        if ref_tweet['type'] == 'replied_to':
                            processed_tweet['is_reply'] = True
                        elif ref_tweet['type'] == 'retweeted':
                            processed_tweet['is_retweet'] = True
                
                processed_data['tweets'].append(processed_tweet)
        
        return processed_data
    
    def _check_rate_limits(self, endpoint_type):
        """
        Check if API request is within rate limits
        
        Args:
            endpoint_type (str): Type of endpoint ('tweets', 'timeline', etc.)
            
        Returns:
            dict: Rate limit check result
        """
        self.ensure_one()
        
        # Rate limit windows (requests per 15 minutes)
        rate_limits = {
            'tweets': 300,  # POST /2/tweets
            'timeline': 75,  # GET /2/users/:id/tweets
            'user_info': 75,  # GET /2/users/me
        }
        
        # Check if we have rate limit info
        if not self.account_id.rate_limit_reset:
            return {'allowed': True, 'message': 'No rate limit info available'}
        
        # Check if rate limit window has reset
        now = fields.Datetime.now()
        if now >= self.account_id.rate_limit_reset:
            return {'allowed': True, 'message': 'Rate limit window has reset'}
        
        # Check remaining requests
        if self.account_id.rate_limit_remaining <= 0:
            reset_time = self.account_id.rate_limit_reset.strftime('%H:%M:%S')
            return {
                'allowed': False,
                'message': f'Rate limit exceeded. Resets at {reset_time}'
            }
        
        return {'allowed': True, 'message': 'Within rate limits'}
    
    def _create_success_response(self, data=None, message='Success'):
        """Create standardized success response"""
        return {
            'success': True,
            'error': None,
            'message': message,
            'data': data or {},
            'timestamp': fields.Datetime.now().isoformat(),
            'rate_limit': {
                'remaining': self.account_id.rate_limit_remaining,
                'reset_at': self.account_id.rate_limit_reset.isoformat() if self.account_id.rate_limit_reset else None
            }
        }
    
    def _create_error_response(self, error_type, message):
        """Create standardized error response"""
        return {
            'success': False,
            'error': error_type,
            'message': message,
            'data': {},
            'timestamp': fields.Datetime.now().isoformat(),
            'rate_limit': {
                'remaining': self.account_id.rate_limit_remaining,
                'reset_at': self.account_id.rate_limit_reset.isoformat() if self.account_id.rate_limit_reset else None
            }
        }
    
    def upload_media(self, media_data, media_type='image', alt_text=None):
        """
        Upload media for use in tweets
        
        Args:
            media_data (bytes): Media file data
            media_type (str): Type of media ('image', 'video', 'gif')
            alt_text (str): Alt text for accessibility
            
        Returns:
            dict: Standardized response with media_id
        """
        self.ensure_one()
        
        # Check authentication
        if not self.account_id.is_authenticated:
            return self._create_error_response(
                'auth_error',
                'Twitter account is not authenticated'
            )
        
        try:
            # Note: Twitter API v2 media upload requires different endpoint
            # This is a placeholder for media upload functionality
            # Real implementation would use Twitter API v1.1 media upload endpoint
            
            return self._create_error_response(
                'not_implemented',
                'Media upload not yet implemented in this version'
            )
            
        except Exception as e:
            _logger.error(f"Error uploading media: {str(e)}")
            return self._create_error_response(
                'system_error',
                f'Media upload failed: {str(e)}'
            )
    
    @api.model
    def get_service_status(self):
        """Get overall service status"""
        services = self.search([('active', '=', True)])
        
        status = {
            'total_services': len(services),
            'authenticated_accounts': 0,
            'total_tweets_posted': 0,
            'services': []
        }
        
        for service in services:
            if service.account_id.is_authenticated:
                status['authenticated_accounts'] += 1
            
            status['total_tweets_posted'] += service.total_tweets_posted
            
            status['services'].append({
                'id': service.id,
                'name': service.name,
                'account_name': service.account_id.name,
                'is_authenticated': service.account_id.is_authenticated,
                'tweets_posted': service.total_tweets_posted,
                'last_tweet': service.last_tweet_time.isoformat() if service.last_tweet_time else None
            })
        
        return status
    
    def action_post_tweet(self):
        """Action method to post tweet from form view"""
        self.ensure_one()
        
        if not self.tweet_text:
            raise UserError(_('Please enter tweet text'))
        
        result = self.post_tweet(self.tweet_text)
        
        # Clear the text field after posting
        self.tweet_text = False
        
        if result.get('success'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Tweet posted successfully!'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Failed to post tweet: %s') % result.get('message', 'Unknown error'),
                    'type': 'danger',
                }
            }
    
    def action_get_timeline(self):
        """Action method to get timeline from form view"""
        self.ensure_one()
        
        result = self.get_user_timeline()
        
        if result.get('success'):
            tweet_count = len(result.get('data', {}).get('tweets', []))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Retrieved %d tweets from timeline') % tweet_count,
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Failed to get timeline: %s') % result.get('message', 'Unknown error'),
                    'type': 'danger',
                }
            }