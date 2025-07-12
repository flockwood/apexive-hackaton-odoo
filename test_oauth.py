#!/usr/bin/env python3
"""
Simple test script to trigger Twitter OAuth flow and capture errors
"""
import requests
import json

# Test OAuth authorization URL generation
def test_twitter_oauth():
    print("Testing Twitter OAuth URL generation...")
    
    # Simulate the parameters that would be sent to Twitter
    test_params = {
        'client_id': 'test_client_id_1234567890',  # Sample client ID
        'redirect_uri': 'http://localhost:8069/twitter/oauth/callback',
        'scope': 'tweet.read tweet.write users.read',
        'response_type': 'code',
        'code_challenge': 'sample_code_challenge_123',
        'code_challenge_method': 'S256',
        'state': 'sample_state_123'
    }
    
    # Build the URL manually to test
    from urllib.parse import urlencode
    base_url = 'https://twitter.com/i/oauth2/authorize'
    params_string = urlencode(test_params)
    authorization_url = f"{base_url}?{params_string}"
    
    print(f"Generated URL: {authorization_url}")
    print(f"URL Length: {len(authorization_url)}")
    
    # Test URL validity
    try:
        response = requests.head(authorization_url, timeout=10, allow_redirects=False)
        print(f"URL Test Response: {response.status_code}")
        if response.status_code == 400:
            print("❌ Got 400 error from Twitter!")
            print(f"Response headers: {dict(response.headers)}")
    except Exception as e:
        print(f"URL test failed: {e}")

if __name__ == "__main__":
    test_twitter_oauth()