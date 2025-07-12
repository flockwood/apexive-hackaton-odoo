from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
from requests_oauthlib import OAuth2Session
import json
import logging

_logger = logging.getLogger(__name__)


class TwitterAccount(models.Model):
    _name = 'twitter.account'
    _description = 'Twitter Account Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Account Name',
        required=True,
        help='Friendly name for this Twitter account'
    )
    
    # OAuth 2.0 Configuration
    client_id = fields.Char(
        string='Client ID',
        required=True,
        help='Twitter API Client ID (from Developer Portal)'
    )
    
    client_secret = fields.Char(
        string='Client Secret',
        required=True,
        help='Twitter API Client Secret (from Developer Portal)'
    )
    
    redirect_uri = fields.Char(
        string='Redirect URI',
        default='http://localhost:8069/twitter/oauth/callback',
        required=True,
        help='OAuth callback URL registered in Twitter app (must match exactly)'
    )
    
    # Authentication State
    access_token = fields.Text(
        string='Access Token',
        help='OAuth 2.0 access token for API calls'
    )
    
    refresh_token = fields.Text(
        string='Refresh Token',
        help='OAuth 2.0 refresh token for token renewal'
    )
    
    token_expires_at = fields.Datetime(
        string='Token Expires At',
        help='When the current access token expires'
    )
    
    is_authenticated = fields.Boolean(
        string='Is Authenticated',
        compute='_compute_is_authenticated',
        store=True,
        help='Whether this account has valid authentication'
    )
    
    # Twitter User Info
    twitter_user_id = fields.Char(
        string='Twitter User ID',
        help='Twitter user ID from API'
    )
    
    twitter_username = fields.Char(
        string='Twitter Username',
        help='Twitter username (@handle)'
    )
    
    twitter_display_name = fields.Char(
        string='Twitter Display Name',
        help='Twitter display name'
    )
    
    # Rate Limiting
    rate_limit_remaining = fields.Integer(
        string='Rate Limit Remaining',
        default=0,
        help='Remaining API calls in current window'
    )
    
    rate_limit_reset = fields.Datetime(
        string='Rate Limit Reset',
        help='When rate limit window resets'
    )
    
    # Status
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this account is active'
    )
    
    last_sync = fields.Datetime(
        string='Last Sync',
        help='Last time this account was synchronized'
    )
    
    # OAuth state for callback validation
    state = fields.Char(
        string='OAuth State',
        help='OAuth state parameter for callback validation'
    )
    
    @api.depends('access_token', 'token_expires_at')
    def _compute_is_authenticated(self):
        for record in self:
            record.is_authenticated = bool(
                record.access_token and 
                (not record.token_expires_at or 
                 record.token_expires_at > fields.Datetime.now())
            )
    
    @api.constrains('client_id', 'client_secret')
    def _check_credentials(self):
        for record in self:
            if not record.client_id or not record.client_secret:
                raise ValidationError(_('Client ID and Client Secret are required'))
    
    def action_authenticate(self):
        """Start OAuth 2.0 authentication flow"""
        self.ensure_one()
        
        # Validate credentials first
        if not self.client_id or not self.client_secret:
            raise UserError(_('Client ID and Client Secret are required'))
        
        if not self.redirect_uri:
            raise UserError(_('Redirect URI is required'))
        
        # Validate redirect URI format
        if not self.redirect_uri.startswith('http://localhost:8069/'):
            raise UserError(_('Redirect URI must start with http://localhost:8069/'))
        
        # Check for common issues
        if len(self.client_id.strip()) < 10:
            raise UserError(_('Client ID appears to be invalid (too short)'))
        
        if len(self.client_secret.strip()) < 10:
            raise UserError(_('Client Secret appears to be invalid (too short)'))
        
        try:
            import secrets
            import base64
            import hashlib
            
            _logger.info(f"Starting OAuth flow for account: {self.name}")
            _logger.info(f"Client ID: {self.client_id[:10]}...")
            _logger.info(f"Redirect URI: {self.redirect_uri}")
            
            # Generate PKCE parameters for Twitter OAuth 2.0
            code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode('utf-8')).digest()
            ).decode('utf-8').rstrip('=')
            
            # Generate state parameter
            state = secrets.token_urlsafe(32)
            
            _logger.info(f"Generated PKCE parameters - Code verifier length: {len(code_verifier)}")
            _logger.info(f"Code challenge: {code_challenge[:20]}...")
            _logger.info(f"State: {state[:20]}...")
            
            # Store parameters for token exchange
            self.write({
                'state': state,
                'access_token': code_verifier  # Temporarily store code_verifier
            })
            
            # Build authorization URL with proper encoding
            auth_params = {
                'response_type': 'code',
                'client_id': self.client_id.strip(),
                'redirect_uri': self.redirect_uri.strip(),
                'scope': 'tweet.read tweet.write users.read',
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'
            }
            
            # Create authorization URL
            from urllib.parse import urlencode, quote
            base_url = 'https://twitter.com/i/oauth2/authorize'
            
            # Manual encoding to ensure proper format
            params_string = '&'.join([f"{k}={quote(str(v), safe='')}" for k, v in auth_params.items()])
            authorization_url = f"{base_url}?{params_string}"
            
            _logger.info(f"Generated OAuth URL: {authorization_url}")
            
            # Validate URL length (Twitter has limits)
            if len(authorization_url) > 2048:
                raise UserError(_('Generated OAuth URL is too long'))
            
            return {
                'type': 'ir.actions.act_url',
                'url': authorization_url,
                'target': 'new',
            }
            
        except Exception as e:
            _logger.error(f"OAuth URL generation failed: {str(e)}")
            raise UserError(_('Failed to generate authentication URL: %s') % str(e))
    
    def complete_authentication(self, code, state):
        """Complete OAuth 2.0 authentication with authorization code"""
        self.ensure_one()
        
        try:
            _logger.info(f"Completing authentication for account {self.name} with code: {code[:10]}...")
            
            # Verify state matches
            if self.state != state:
                raise UserError(_('Invalid state parameter. Please try authentication again.'))
            
            # Get stored code_verifier
            code_verifier = self.access_token
            if not code_verifier:
                raise UserError(_('Code verifier not found. Please restart authentication.'))
            
            # Prepare token exchange request
            token_data = {
                'grant_type': 'authorization_code',
                'client_id': self.client_id,
                'code_verifier': code_verifier,
                'redirect_uri': self.redirect_uri,
                'code': code
            }
            
            # Make token exchange request with proper authentication
            import requests
            import base64
            
            # Prepare Basic Auth header for client credentials
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {auth_b64}'
            }
            
            _logger.info(f"Making token exchange request with data: {token_data}")
            _logger.info(f"Request headers: Content-Type and Authorization set")
            
            response = requests.post(
                'https://api.twitter.com/2/oauth2/token',
                data=token_data,
                headers=headers,
                timeout=30
            )
            
            _logger.info(f"Token exchange response: {response.status_code}")
            _logger.info(f"Response headers: {dict(response.headers)}")
            _logger.info(f"Response body: {response.text}")
            
            if response.status_code != 200:
                _logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                raise UserError(_('Token exchange failed: %s - %s') % (response.status_code, response.text))
            
            token = response.json()
            _logger.info(f"Token exchange successful: {list(token.keys())}")
            
            # Store tokens
            self.write({
                'access_token': json.dumps(token),
                'refresh_token': token.get('refresh_token'),
                'token_expires_at': fields.Datetime.now().replace(
                    second=0, microsecond=0
                ) + fields.timedelta(seconds=token.get('expires_in', 7200))
            })
            
            # Get user info
            self._fetch_user_info()
            
            return True
            
        except Exception as e:
            _logger.error(f"Twitter OAuth error: {str(e)}")
            raise UserError(_('Authentication failed: %s') % str(e))
    
    def _fetch_user_info(self):
        """Fetch user information from Twitter API"""
        self.ensure_one()
        
        try:
            response = self._make_api_request(
                'GET',
                'https://api.twitter.com/2/users/me',
                params={'user.fields': 'id,username,name'}
            )
            
            if response.get('success') and response.get('data'):
                user_data = response['data']['data']
                self.write({
                    'twitter_user_id': user_data.get('id'),
                    'twitter_username': user_data.get('username'),
                    'twitter_display_name': user_data.get('name'),
                    'last_sync': fields.Datetime.now()
                })
                
        except Exception as e:
            _logger.error(f"Failed to fetch user info: {str(e)}")
    
    def _make_api_request(self, method, url, params=None, data=None, headers=None):
        """Make authenticated API request to Twitter"""
        self.ensure_one()
        
        if not self.is_authenticated:
            raise UserError(_('Account is not authenticated'))
        
        # Parse stored token
        try:
            token_data = json.loads(self.access_token)
            access_token = token_data.get('access_token')
        except:
            raise UserError(_('Invalid access token'))
        
        # Prepare headers
        request_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        if headers:
            request_headers.update(headers)
        
        try:
            # Make request
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=request_headers,
                timeout=30
            )
            
            # Update rate limit info
            self._update_rate_limit_info(response)
            
            # Handle response
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json(),
                    'status_code': response.status_code
                }
            elif response.status_code == 429:
                # Rate limited
                return {
                    'success': False,
                    'error': 'rate_limited',
                    'message': 'API rate limit exceeded',
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': False,
                    'error': 'api_error',
                    'message': response.text,
                    'status_code': response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            _logger.error(f"Twitter API request failed: {str(e)}")
            return {
                'success': False,
                'error': 'network_error',
                'message': str(e),
                'status_code': None
            }
    
    def _update_rate_limit_info(self, response):
        """Update rate limit information from response headers"""
        self.ensure_one()
        
        try:
            remaining = response.headers.get('x-rate-limit-remaining')
            reset_time = response.headers.get('x-rate-limit-reset')
            
            if remaining:
                self.rate_limit_remaining = int(remaining)
            
            if reset_time:
                import datetime
                self.rate_limit_reset = datetime.datetime.fromtimestamp(
                    int(reset_time)
                )
                
        except Exception as e:
            _logger.warning(f"Could not parse rate limit headers: {str(e)}")
    
    def refresh_access_token(self):
        """Refresh the access token using refresh token"""
        self.ensure_one()
        
        if not self.refresh_token:
            raise UserError(_('No refresh token available'))
        
        try:
            # Prepare refresh request
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id
            }
            
            response = requests.post(
                'https://api.twitter.com/2/oauth2/token',
                data=data,
                auth=(self.client_id, self.client_secret),
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                self.write({
                    'access_token': json.dumps(token_data),
                    'refresh_token': token_data.get('refresh_token', self.refresh_token),
                    'token_expires_at': fields.Datetime.now().replace(
                        second=0, microsecond=0
                    ) + fields.timedelta(seconds=token_data.get('expires_in', 7200))
                })
                
                return True
            else:
                raise UserError(_('Token refresh failed: %s') % response.text)
                
        except Exception as e:
            _logger.error(f"Token refresh error: {str(e)}")
            raise UserError(_('Token refresh failed: %s') % str(e))
    
    def test_connection(self):
        """Test API connection"""
        self.ensure_one()
        
        try:
            response = self._make_api_request(
                'GET',
                'https://api.twitter.com/2/users/me'
            )
            
            if response.get('success'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Twitter API connection successful'),
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('Connection failed: %s') % response.get('message', 'Unknown error'),
                        'type': 'danger',
                    }
                }
                
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Connection test failed: %s') % str(e),
                    'type': 'danger',
                }
            }