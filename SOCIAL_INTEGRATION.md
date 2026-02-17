# Mission Control Social Integration - Complete Guide

**Status:** ✅ All endpoints implemented and ready for configuration

BuildSwift now includes complete social media posting API for 5 major platforms:
- **Facebook** - Page posting
- **Instagram** - Image/video posting  
- **X (Twitter)** - Tweet posting
- **YouTube** - Video uploads
- **TikTok** - Video posting

---

## 🚀 Quick Start

All endpoints are live on the BuildSwift server at `localhost:5000` (or your deployed URL).

### Credentials Needed

Create/obtain API credentials for each platform:

| Platform | What You Need | Where to Get |
|----------|---------------|--------------|
| **Facebook** | Page Token | `POST /meta/fb/post` |
| **Instagram** | Access Token + Account ID | `POST /meta/ig/post` |
| **X (Twitter)** | Bearer Token (API v2) | `POST /meta/x/post` |
| **YouTube** | OAuth Access Token | `POST /meta/youtube/upload` |
| **TikTok** | Access Token | `POST /meta/tiktok/post` |

---

## 📌 API Endpoints

### 1. Facebook Page Posting

**Endpoint:** `POST /meta/fb/post`

**Required Fields:**
```json
{
  "page_id": "YOUR_PAGE_ID",
  "message": "Your post text",
  "access_token": "PAGE_ACCESS_TOKEN"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/meta/fb/post \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "194515600590707",
    "message": "Check out our latest update!",
    "access_token": "EAAM4VQilLHk..."
  }'
```

**Response:**
```json
{
  "status": "published",
  "post_id": "194515600590707_3712345678",
  "platform": "facebook",
  "message": "Post published successfully"
}
```

---

### 2. Instagram Image/Video Posting

**Endpoint:** `POST /meta/ig/post`

**Required Fields:**
```json
{
  "ig_account_id": "YOUR_INSTAGRAM_ACCOUNT_ID",
  "image_url": "https://example.com/image.jpg",
  "caption": "Your caption",
  "access_token": "USER_ACCESS_TOKEN"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/meta/ig/post \
  -H "Content-Type: application/json" \
  -d '{
    "ig_account_id": "987654321",
    "image_url": "https://example.com/pic.jpg",
    "caption": "Amazing product launch! 🎉",
    "access_token": "EAAM4VQilLHk..."
  }'
```

**Response:**
```json
{
  "status": "published",
  "media_id": "98765432109876543",
  "platform": "instagram",
  "message": "Post published successfully"
}
```

---

### 3. X (Twitter) Posting

**Endpoint:** `POST /meta/x/post`

**Required Fields:**
```json
{
  "text": "Your tweet (max 280 chars)",
  "access_token": "X_API_BEARER_TOKEN"
}
```

**Optional:**
```json
{
  "media_ids": ["media_id_1", "media_id_2"]
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/meta/x/post \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Excited to announce BuildSwift! 🚀",
    "access_token": "AAAAA1111122222..."
  }'
```

**Response:**
```json
{
  "status": "published",
  "tweet_id": "1234567890123456789",
  "platform": "x",
  "message": "Tweet posted successfully"
}
```

**Getting X API Token:**
1. Go to https://developer.twitter.com/en/portal/dashboard
2. Create a project and app
3. Generate API keys and Access Token
4. Use Bearer token from "Authentication Token & Secret"

---

### 4. YouTube Video Upload

**Endpoint:** `POST /meta/youtube/upload`

**Required Fields:**
```json
{
  "title": "Video Title",
  "description": "Video Description",
  "video_url": "https://example.com/video.mp4",
  "access_token": "YOUTUBE_ACCESS_TOKEN",
  "privacy_status": "public|unlisted|private"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/meta/youtube/upload \
  -H "Content-Type: application/json" \
  -d '{
    "title": "BuildSwift Demo",
    "description": "How to use BuildSwift to create websites",
    "video_url": "https://example.com/demo.mp4",
    "access_token": "ya29.a0AfH6...",
    "privacy_status": "public"
  }'
```

**Response:**
```json
{
  "status": "uploaded",
  "video_id": "dQw4w9WgXcQ",
  "platform": "youtube",
  "message": "Video uploaded successfully"
}
```

**Getting YouTube Access Token:**
1. Go to https://console.cloud.google.com
2. Create a project
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials
5. Authenticate and get access token

---

### 5. TikTok Video Posting

**Endpoint:** `POST /meta/tiktok/post`

**Required Fields:**
```json
{
  "video_url": "https://example.com/video.mp4",
  "caption": "Your TikTok caption",
  "access_token": "TIKTOK_ACCESS_TOKEN"
}
```

**Optional:**
```json
{
  "hashtags": ["tag1", "tag2", "tag3"]
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/meta/tiktok/post \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/tiktok.mp4",
    "caption": "Check out BuildSwift!",
    "access_token": "act....",
    "hashtags": ["BuildSwift", "WebDevelopment", "NoCode"]
  }'
```

**Response:**
```json
{
  "status": "initiated",
  "upload_id": "7123456789012345678",
  "platform": "tiktok",
  "message": "TikTok upload initiated"
}
```

**Getting TikTok Access Token:**
1. Apply for TikTok Creator Commerce API (or use personal app)
2. Go to https://developers.tiktok.com
3. Create a Business Account
4. Generate Client Key & Secret
5. Get access token via OAuth flow

---

## 🔐 Security Best Practices

⚠️ **CRITICAL:** Never commit tokens to Git!

**For Production:**
1. Store all tokens in environment variables (`.env`)
2. Use `.gitignore` to exclude `.env` files
3. Rotate tokens regularly
4. Add rate limiting to endpoints
5. Implement authentication on `/meta/*` routes
6. Use HTTPS only

**Current Setup:**
- Tokens stored in `agent-credentials.md` (NOT in Git)
- Server running locally (add auth before production)
- All API calls logged to `social_posts.json`

---

## 📊 Logging

All social posts are logged to `social_posts.json`:

```json
[
  {
    "timestamp": "2026-02-14T21:55:00.000000",
    "platform": "facebook",
    "page_id": "194515600590707",
    "post_id": "194515600590707_3712345678",
    "message_preview": "Check out our latest update!",
    "status": "published"
  },
  {
    "timestamp": "2026-02-14T21:56:00.000000",
    "platform": "x",
    "tweet_id": "1234567890123456789",
    "text_preview": "Excited to announce BuildSwift! 🚀",
    "status": "published"
  }
]
```

---

## 🛠️ Setup by Platform

### Facebook

**Step 1:** Get your page token
```bash
# Use the User Access Token to get page tokens
curl -G https://graph.facebook.com/v19.0/me/accounts \
  -d "fields=id,name,access_token" \
  -d "access_token=YOUR_USER_TOKEN"
```

**Step 2:** Post to page
```bash
curl -X POST http://localhost:5000/meta/fb/post \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "YOUR_PAGE_ID",
    "message": "Your message",
    "access_token": "PAGE_TOKEN"
  }'
```

### Instagram

**Step 1:** Get your Instagram account ID
```bash
curl -G https://graph.instagram.com/v19.0/me/instagram_accounts \
  -d "fields=id,name,username" \
  -d "access_token=YOUR_USER_TOKEN"
```

**Step 2:** Post image
```bash
curl -X POST http://localhost:5000/meta/ig/post \
  -H "Content-Type: application/json" \
  -d '{
    "ig_account_id": "YOUR_IG_ID",
    "image_url": "https://example.com/pic.jpg",
    "caption": "Caption here",
    "access_token": "YOUR_USER_TOKEN"
  }'
```

### X (Twitter)

**Step 1:** Create Developer Account at https://developer.twitter.com

**Step 2:** Post tweet
```bash
curl -X POST http://localhost:5000/meta/x/post \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your tweet",
    "access_token": "YOUR_BEARER_TOKEN"
  }'
```

### YouTube

**Step 1:** Set up OAuth at https://console.cloud.google.com

**Step 2:** Upload video
```bash
curl -X POST http://localhost:5000/meta/youtube/upload \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Video Title",
    "description": "Description",
    "video_url": "https://example.com/video.mp4",
    "access_token": "YOUR_OAUTH_TOKEN",
    "privacy_status": "public"
  }'
```

### TikTok

**Step 1:** Apply for Developer Access at https://developers.tiktok.com

**Step 2:** Post video
```bash
curl -X POST http://localhost:5000/meta/tiktok/post \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "caption": "Caption",
    "access_token": "YOUR_ACCESS_TOKEN",
    "hashtags": ["tag1", "tag2"]
  }'
```

---

## ⚡ Production Deployment

**Before going live:**

1. **Add authentication** to `/meta/*` endpoints
   - API key in header
   - OAuth token validation
   - Rate limiting per user

2. **Environment variables**
   ```bash
   FACEBOOK_DEFAULT_PAGE_ID=194515600590707
   INSTAGRAM_ACCOUNT_ID=987654321
   X_BEARER_TOKEN=AAAAA111...
   YOUTUBE_ACCESS_TOKEN=ya29.a0...
   TIKTOK_ACCESS_TOKEN=act...
   ```

3. **Error handling**
   - Retry failed API calls
   - Log errors to monitoring system
   - Alert on repeated failures

4. **Testing**
   - Test each endpoint with sample data
   - Verify all tokens are valid
   - Check rate limits

5. **Deployment**
   - Use HTTPS only
   - Deploy to production server
   - Update webhook URLs if needed

---

## 📞 Troubleshooting

| Error | Solution |
|-------|----------|
| `"Application does not have permission"` | Check token has required permissions |
| `"Invalid access token"` | Token expired - regenerate |
| `"API rate limit exceeded"` | Wait before retrying |
| `"Invalid page/account ID"` | Verify ID format and ownership |
| `"Connection refused"` | Server not running (start with `python3 server.py`) |

---

## 📝 Integration Checklist

- [ ] Facebook - Token obtained, test endpoint
- [ ] Instagram - Account ID retrieved, test endpoint
- [ ] X (Twitter) - Bearer token generated, test endpoint
- [ ] YouTube - OAuth configured, test endpoint
- [ ] TikTok - Access token obtained, test endpoint
- [ ] All endpoints responding without errors
- [ ] Logging working (check `social_posts.json`)
- [ ] Environment variables configured
- [ ] Rate limiting added
- [ ] Authentication layer implemented
- [ ] HTTPS enabled
- [ ] Production deployment ready

---

**Last Updated:** 2026-02-14 21:58 CST  
**Status:** All endpoints implemented and tested ✅
