#!/usr/bin/env python3
"""
Twitter OAuth 2.0 Setup Script

This script helps you get OAuth 2.0 tokens with refresh capability.
Run once, then the tokens auto-refresh forever.

Usage:
    python3 scripts/twitter_oauth2_setup.py

Requirements:
    - TWITTER_CLIENT_ID in your .env (from Twitter Developer Portal)
    - TWITTER_CLIENT_SECRET in your .env (from Twitter Developer Portal)
"""

import os
import sys
import base64
import hashlib
import secrets
import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.expanduser("~/.openclaw/.env"))

CLIENT_ID = os.environ.get("TWITTER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("TWITTER_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:8000/callback"
SCOPES = "tweet.read tweet.write users.read offline.access"

# PKCE helpers
def generate_code_verifier():
    return secrets.token_urlsafe(32)

def generate_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()

class CallbackHandler(BaseHTTPRequestHandler):
    """Handle the OAuth callback."""
    code = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if 'code' in query:
            CallbackHandler.code = query['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>Success!</h1>
                <p>Authorization code received. You can close this window.</p>
                <p>Return to your terminal to see the tokens.</p>
                </body></html>
            """)
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Error: No code received")

    def log_message(self, format, *args):
        pass  # Suppress logging

def main():
    if not CLIENT_ID:
        print("\n❌ TWITTER_CLIENT_ID not found in ~/.openclaw/.env")
        print("\nTo get your Client ID:")
        print("1. Go to: https://developer.twitter.com/en/portal/projects-and-apps")
        print("2. Click on your app → 'Keys and tokens' tab")
        print("3. Under 'OAuth 2.0 Client ID and Client Secret', copy the Client ID")
        print("4. Add to ~/.openclaw/.env: TWITTER_CLIENT_ID=your_client_id")
        print("5. Also add: TWITTER_CLIENT_SECRET=your_client_secret")
        sys.exit(1)

    print("\n🐦 Twitter OAuth 2.0 Setup")
    print("=" * 50)

    # Generate PKCE values
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(16)

    # Build authorization URL
    auth_params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    auth_url = f"https://twitter.com/i/oauth2/authorize?{urlencode(auth_params)}"

    print(f"\n1. Opening browser for authorization...")
    print(f"   If browser doesn't open, visit:\n   {auth_url}\n")

    # Start callback server
    server = HTTPServer(('127.0.0.1', 8000), CallbackHandler)

    # Open browser
    webbrowser.open(auth_url)

    print("2. Waiting for authorization callback...")

    # Wait for callback
    while CallbackHandler.code is None:
        server.handle_request()

    code = CallbackHandler.code
    print(f"\n3. ✅ Authorization code received!")

    # Exchange code for tokens
    print("\n4. Exchanging code for tokens...")

    token_data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier
    }

    # Use client secret if available (confidential client)
    if CLIENT_SECRET:
        auth = (CLIENT_ID, CLIENT_SECRET)
    else:
        auth = None
        token_data["client_id"] = CLIENT_ID

    response = requests.post(
        "https://api.twitter.com/2/oauth2/token",
        data=token_data,
        auth=auth,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    if response.status_code != 200:
        print(f"\n❌ Error getting tokens: {response.text}")
        sys.exit(1)

    tokens = response.json()

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 7200)

    print("\n" + "=" * 50)
    print("✅ SUCCESS! Here are your tokens:")
    print("=" * 50)

    print(f"\nAccess Token (expires in {expires_in}s):")
    print(f"TWITTER_OAUTH2_ACCESS_TOKEN={access_token}")

    if refresh_token:
        print(f"\nRefresh Token (use this to auto-refresh):")
        print(f"TWITTER_OAUTH2_REFRESH_TOKEN={refresh_token}")
    else:
        print("\n⚠️  No refresh token received. Make sure 'offline.access' scope is enabled.")

    # Update .env file
    env_path = os.path.expanduser("~/.openclaw/.env")
    print(f"\n5. Updating {env_path}...")

    with open(env_path, 'r') as f:
        env_content = f.read()

    # Update or add tokens
    import re

    if "TWITTER_OAUTH2_ACCESS_TOKEN=" in env_content:
        env_content = re.sub(
            r'TWITTER_OAUTH2_ACCESS_TOKEN=.*',
            f'TWITTER_OAUTH2_ACCESS_TOKEN={access_token}',
            env_content
        )
    else:
        env_content += f"\nTWITTER_OAUTH2_ACCESS_TOKEN={access_token}"

    if refresh_token:
        if "TWITTER_OAUTH2_REFRESH_TOKEN=" in env_content:
            env_content = re.sub(
                r'TWITTER_OAUTH2_REFRESH_TOKEN=.*',
                f'TWITTER_OAUTH2_REFRESH_TOKEN={refresh_token}',
                env_content
            )
        else:
            env_content += f"\nTWITTER_OAUTH2_REFRESH_TOKEN={refresh_token}"

    with open(env_path, 'w') as f:
        f.write(env_content)

    print("\n✅ Tokens saved to .env file!")
    print("\nThe twitter-mcp server will now auto-refresh tokens when they expire.")
    print("You should never need to run this script again.")

if __name__ == "__main__":
    main()
