# Meta Developer Integration - Mission Control Social

**Status:** ✅ API Endpoints Ready | ⏳ Awaiting Access Tokens

## Overview

Mission Control Social app (App ID: `906362798550137`) is configured to integrate with:
- **Facebook Graph API** - Page posting & engagement management
- **Instagram Graph API** - Content publishing & messaging

## Current Setup

### App Credentials ✅
- **App ID:** 906362798550137
- **App Secret:** 7d4fee6fb98bea7b66258d082d82d9b3 (stored securely)
- **App Token:** 906362798550137|haFK9vR9GUaeXgC3nj-Obu8McUE
- **Use Cases:** 
  - Manage everything on your Page (Facebook)
  - Manage messaging & content on Instagram

### API Endpoints

BuildSwift server now includes two Meta integration endpoints:

#### 1. Facebook Page Posting
**Endpoint:** `POST /meta/fb/post`

**Description:** Publish a post to a Facebook page

**Request Payload:**
```json
{
  "page_id": "YOUR_FACEBOOK_PAGE_ID",
  "message": "Your post content here",
  "access_token": "PAGE_ACCESS_TOKEN"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/meta/fb/post \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "12345678",
    "message": "Hello from Mission Control!",
    "access_token": "YOUR_PAGE_TOKEN_HERE"
  }'
```

**Response:**
```json
{
  "status": "published",
  "post_id": "12345678_98765432",
  "platform": "facebook",
  "message": "Post published successfully"
}
```

---

#### 2. Instagram Content Posting
**Endpoint:** `POST /meta/ig/post`

**Description:** Publish image content to Instagram account

**Request Payload:**
```json
{
  "ig_account_id": "YOUR_INSTAGRAM_ACCOUNT_ID",
  "image_url": "https://example.com/image.jpg",
  "caption": "Your post caption",
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
    "caption": "Check out our new feature!",
    "access_token": "YOUR_USER_TOKEN_HERE"
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

## Getting Access Tokens

### Step 1: User Access Token (Facebook/Instagram)

1. Log in to [Facebook Developer App](https://developers.facebook.com/apps/906362798550137/)
2. Go to **Tools** → **Graph API Explorer**
3. Select your app from the dropdown
4. Click **Generate Access Token**
5. Accept the requested permissions:
   - `pages_read_engagement`
   - `pages_manage_posts`
   - `pages_manage_metadata` (Facebook)
   - `instagram_basic`
   - `instagram_content_publishing` (Instagram)

Your User Access Token will be displayed (looks like: `EAA...` format)

### Step 2: Page Access Token (Facebook Only)

If posting to a Facebook Page, you need a **Page Access Token**:

```bash
curl -G https://graph.facebook.com/v19.0/{PAGE_ID} \
  -d "fields=access_token" \
  -d "access_token={USER_ACCESS_TOKEN}"
```

Response:
```json
{
  "access_token": "EAAB...",  // This is your Page Access Token
  "id": "12345678"
}
```

### Step 3: Instagram Account ID

To find your Instagram account ID connected to Facebook:

```bash
curl -G https://graph.facebook.com/v19.0/me/instagram_accounts \
  -d "fields=id,name,username" \
  -d "access_token={USER_ACCESS_TOKEN}"
```

Response:
```json
{
  "data": [
    {
      "id": "987654321",
      "name": "My Instagram",
      "username": "myusername"
    }
  ]
}
```

---

## Logging

All social media posts are logged to `social_posts.json`:

```json
[
  {
    "timestamp": "2026-02-14T21:30:00.000000",
    "platform": "facebook",
    "page_id": "12345678",
    "post_id": "12345678_98765432",
    "message_preview": "Hello from Mission Control!",
    "status": "published"
  },
  {
    "timestamp": "2026-02-14T21:31:00.000000",
    "platform": "instagram",
    "ig_account_id": "987654321",
    "media_id": "98765432109876543",
    "caption_preview": "Check out our new feature!",
    "status": "published"
  }
]
```

---

## Security Notes

⚠️ **Important:**
- Never commit access tokens to Git
- Regenerate tokens if they're accidentally exposed
- Use environment variables for production deployments
- Add authentication checks to `/meta/*` endpoints before production

---

## Next Steps

### Immediate (Today)
- [ ] Generate User Access Token via Graph API Explorer
- [ ] Test `/meta/fb/post` endpoint with real page ID
- [ ] Test `/meta/ig/post` endpoint with real Instagram account

### Short Term
- [ ] Add API key authentication to `/meta/*` endpoints
- [ ] Create management dashboard for social posting
- [ ] Add scheduling support for future posts
- [ ] Implement image upload instead of image_url

### Long Term
- [ ] Multi-account support (multiple Facebook pages / Instagram accounts)
- [ ] Analytics dashboard (impressions, engagement, reach)
- [ ] Team collaboration features
- [ ] Content approval workflow

---

## Troubleshooting

### "Invalid access token"
- Token may be expired (typically 60 days)
- Token may not have required permissions
- Solution: Generate a new token with all required permissions

### "Instagram API error: (#100)"
- Account ID or token is incorrect
- Solution: Verify account ID using the curl command above

### "Facebook API error: Invalid POST arguments"
- Missing required fields (page_id, message, access_token)
- Solution: Check request payload matches documented format

---

## Resources

- [Facebook Graph API Docs](https://developers.facebook.com/docs/graph-api)
- [Instagram Graph API Docs](https://developers.instagram.com/docs/instagram-api)
- [Access Token Guide](https://developers.facebook.com/docs/facebook-login/access-tokens)
- [Meta Developer Dashboard](https://developers.facebook.com/apps/906362798550137/)

---

**Last Updated:** 2026-02-14 21:24 CST  
**Integration Status:** Ready for Testing ✅
