{
    'name': 'Twitter API Service',
    'version': '16.0.1.0.0',
    'category': 'Social Media',
    'summary': 'Twitter API integration with OAuth 2.0, posting, and timeline retrieval',
    'description': """
Twitter API Service Module
==========================

This module provides comprehensive Twitter API integration including:
- OAuth 2.0 authentication flow
- Post tweets immediately
- Retrieve user timeline
- Graceful rate limiting handling  
- Standardized response format

Features:
- Secure OAuth 2.0 authentication
- Real-time tweet posting
- Timeline data retrieval
- Rate limit management
- Error handling and logging
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/templates/oauth_templates.xml',
        'views/twitter_account_views.xml',
        'views/twitter_service_views.xml',
        'views/menu_views.xml',
        'wizards/twitter_auth_wizard_views.xml',
    ],
    'assets': {
        'web.assets_common': [
            'twitter_api_service/static/src/js/underscore_polyfill.js',
        ],
        'web.assets_backend': [
            'twitter_api_service/static/src/js/twitter_oauth.js',
        ],
    },
    'external_dependencies': {
        'python': ['requests', 'requests_oauthlib'],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}