from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TwitterAuthWizard(models.TransientModel):
    _name = 'twitter.auth.wizard'
    _description = 'Twitter Authentication Wizard'

    account_id = fields.Many2one(
        'twitter.account',
        string='Twitter Account',
        required=True
    )
    
    auth_url = fields.Char(
        string='Authentication URL',
        readonly=True,
        help='Copy this URL to your browser to authenticate'
    )
    
    auth_code = fields.Char(
        string='Authorization Code',
        help='Paste the authorization code you received from Twitter'
    )
    
    state = fields.Selection([
        ('start', 'Start'),
        ('waiting', 'Waiting for Authorization'),
        ('complete', 'Complete')
    ], default='start', string='State')

    def action_start_auth(self):
        """Start the authentication process"""
        self.ensure_one()
        
        # Generate authorization URL
        result = self.account_id.action_authenticate()
        
        if result.get('url'):
            self.write({
                'auth_url': result['url'],
                'state': 'waiting'
            })
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'twitter.auth.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': self.env.context
            }
        else:
            raise UserError(_('Failed to generate authentication URL'))

    def action_complete_auth(self):
        """Complete the authentication with the provided code"""
        self.ensure_one()
        
        if not self.auth_code:
            raise UserError(_('Please provide the authorization code'))
        
        try:
            # This would need the state parameter which should be stored
            # For now, we'll show a message that the user should use the callback URL
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Manual Authentication'),
                    'message': _('Please complete authentication through the callback URL. Manual code entry is not fully implemented in this version.'),
                    'type': 'warning',
                }
            }
            
        except Exception as e:
            raise UserError(_('Authentication failed: %s') % str(e))