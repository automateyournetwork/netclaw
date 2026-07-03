# Quickstart: Twitter/X Integration

**Feature**: 039-twitter-x-integration
**Estimated Setup Time**: 10 minutes

---

## Prerequisites

1. **Twitter Developer Account** with Free tier access
2. **Twitter App** attached to a Project in the Developer Portal
3. **OAuth 1.0a credentials** generated from the app
4. **NetClaw** installed and running

---

## Step 1: Get Twitter API Credentials

1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create or select your Project (e.g., "NetClaw")
3. Create or select an App within the Project
4. Navigate to "Keys and Tokens"
5. Generate and copy:
   - **API Key** (Consumer Key)
   - **API Key Secret** (Consumer Secret)
   - **Access Token**
   - **Access Token Secret**

**Important**: Your App must be attached to a Project for API v2 access.

---

## Step 2: Configure Environment Variables

Add to `~/.openclaw/.env`:

```bash
# Twitter/X Integration
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_SECRET=your_access_token_secret_here

# Heartbeat Configuration (optional)
TWITTER_HEARTBEAT_ENABLED=false  # Set to true to enable autonomous tweeting
TWITTER_HEARTBEAT_INTERVAL=14400  # Seconds between tweets (default: 4 hours)
```

---

## Step 3: Install Twitter MCP Server

```bash
# Run the Twitter installation script
./scripts/twitter_install.sh

# Or manually:
cd mcp-servers/twitter-mcp
pip install -r requirements.txt
```

---

## Step 4: Verify Configuration

Restart the OpenClaw gateway:

```bash
# Restart gateway to load new MCP server
pkill -f "openclaw gateway" && openclaw gateway start
```

Verify the Twitter MCP server is loaded:

```bash
# In NetClaw conversation
"Show me my available Twitter tools"
```

Expected tools:
- `twitter_post_tweet`
- `twitter_post_thread`
- `twitter_post_tweet_with_media`
- `twitter_delete_tweet`
- `twitter_get_rate_limits`

---

## Step 5: Test Manual Tweeting

Ask NetClaw to post a test tweet:

```
"Tweet: Testing NetClaw's new Twitter integration! #netclaw"
```

NetClaw will:
1. Apply content guardrails
2. Show you the tweet preview
3. Ask for confirmation
4. Post to Twitter
5. Return the tweet URL

---

## Step 6: Enable Heartbeat (Optional)

To enable autonomous heartbeat tweets:

1. Set `TWITTER_HEARTBEAT_ENABLED=true` in `.env`
2. Restart the gateway

NetClaw will automatically tweet every 4 hours with:
- CCIE-level network tips
- Technical hot takes
- TIL (Today I Learned) moments
- Sanitized work achievements
- AI/network engineering musings
- Community/career content

---

## Verification Checklist

- [ ] Twitter credentials configured in `~/.openclaw/.env`
- [ ] Twitter MCP server installed (`pip install -r requirements.txt`)
- [ ] Gateway restarted
- [ ] Manual tweet test successful
- [ ] Heartbeat enabled (if desired)

---

## Troubleshooting

### "App not attached to Project" Error

**Symptom**: 403 error mentioning "keys from App attached to Project"

**Solution**:
1. Go to Twitter Developer Portal
2. Ensure your App is inside a Project (not standalone)
3. Regenerate credentials from within the Project context

### Rate Limit Exceeded

**Symptom**: 429 error or "Rate limit exceeded" message

**Solution**:
- Free tier allows 50 tweets per 24 hours
- Wait for rate limit to reset (check with `twitter_get_rate_limits`)
- Reduce heartbeat frequency if needed

### Guardrail Blocking Content

**Symptom**: Tweet rejected by guardrails

**Solution**:
- Check for IP addresses, credentials, or customer names in content
- Use RFC 5737 documentation IPs (192.0.2.x) for examples
- Remove or redact sensitive information

---

## Next Steps

- View tweets in the Visual HUD Twitter panel
- Customize heartbeat interval via `TWITTER_HEARTBEAT_INTERVAL`
- Add customer names to the blocklist for additional protection
- Consider upgrading to Twitter Basic tier ($100/mo) for bidirectional interaction
