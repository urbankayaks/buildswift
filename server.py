#!/usr/bin/env python3
"""
BuildSwift Payment & Deployment Server
Handles Stripe payments, triggers site builds, and deploys to customer domains.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv(Path(__file__).parent / ".env")

import json
import stripe
import hmac
import hashlib
import subprocess
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from urllib.parse import urljoin
from pipeline.builder import build_site

app = Flask(__name__)

# Configuration
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_live_YOUR_KEY_HERE")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_live_YOUR_KEY_HERE")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_YOUR_KEY_HERE")
BUILDS_DIR = Path(__file__).parent / "builds"
PAYMENT_LOG = Path(__file__).parent / "payments.json"

stripe.api_key = STRIPE_SECRET_KEY

# MARK: - Account Mappings (Brand to Social Accounts)

ACCOUNT_MAPPING = {
    "urban_kayaks": {
        "instagram": "@UrbanKayaks",
        "facebook": "194515600590707",  # Urban Kayaks page ID
        "x": "@urbankayaks",
        "youtube": "@UrbanKayaks",
        "tiktok": "@UrbanKayaksChicago"
    },
    "taco_rio": {
        "instagram": "@TacoRio_Chicago",
        "facebook": "109055092235272",  # TacoRio page ID (if exists)
        "tiktok": "@TacoRio_Chicago"
    }
}

# Analytics data per platform per brand
ANALYTICS_DATA = {
    "urban_kayaks": {
        "Instagram": {"platform": "Instagram", "followers": 12000, "engagement": 5.1, "reach": 15000, "impressions": 52000, "reachChange": 7.5},
        "Facebook": {"platform": "Facebook", "followers": 8200, "engagement": 2.8, "reach": 12400, "impressions": 45200, "reachChange": 3.0},
        "X": {"platform": "X", "followers": 1800, "engagement": 1.9, "reach": 4200, "impressions": 12500, "reachChange": -1.0},
        "YouTube": {"platform": "YouTube", "followers": 450, "engagement": 6.7, "reach": 3100, "impressions": 8900, "reachChange": 15.0},
        "TikTok": {"platform": "TikTok", "followers": 2200, "engagement": 7.8, "reach": 18000, "impressions": 65000, "reachChange": 18.0}
    },
    "taco_rio": {
        "Instagram": {"platform": "Instagram", "followers": 11600, "engagement": 5.3, "reach": 8900, "impressions": 28000, "reachChange": 10.0},
        "TikTok": {"platform": "TikTok", "followers": 900, "engagement": 9.2, "reach": 12000, "impressions": 45000, "reachChange": 28.0}
    }
}

# Initialize payment log
if not PAYMENT_LOG.exists():
    PAYMENT_LOG.write_text(json.dumps([], indent=2))


@app.route("/", methods=["GET"])
def index():
    """Serve the landing page with Stripe checkout embedded."""
    return render_template_string(open(Path(__file__).parent / "index.html").read(),
                                   stripe_key=STRIPE_PUBLISHABLE_KEY)


# Stripe Product/Price IDs (Test Mode)
STRIPE_PACKAGES = {
    "premium": {
        "name": "Premium",
        "mode": "payment",
        "line_items": [{"price": "price_1T1jY41FSFhZLQtyqRvLMxyq", "quantity": 1}],
    },
    "standard": {
        "name": "Standard",
        "mode": "payment",
        "line_items": [{"price": "price_1T1jY51FSFhZLQtyZiyjPn6X", "quantity": 1}],
    },
    "all_inclusive": {
        "name": "All-Inclusive",
        "mode": "subscription",
        "line_items": [{"price": "price_1T1jY51FSFhZLQtyJIKwbUSM", "quantity": 1}],
    },
}


@app.route("/api/checkout", methods=["POST"])
def create_checkout():
    """Create a Stripe checkout session for a website build package."""
    try:
        data = request.json
        package = data.get("package", "all_inclusive")
        business_name = data.get("business_name", "")
        email = data.get("email", "")
        industry = data.get("industry", "")

        pkg = STRIPE_PACKAGES.get(package)
        if not pkg:
            return jsonify({"error": f"Unknown package: {package}"}), 400

        session_params = {
            "payment_method_types": ["card"],
            "line_items": pkg["line_items"],
            "mode": pkg["mode"],
            "success_url": urljoin(request.host_url, "/success?session_id={CHECKOUT_SESSION_ID}"),
            "cancel_url": urljoin(request.host_url, "/cancel"),
            "metadata": {
                "package": package,
                "business_name": business_name,
                "industry": industry,
                "email": email,
            },
        }
        if email:
            session_params["customer_email"] = email

        session = stripe.checkout.Session.create(**session_params)

        return jsonify({
            "sessionId": session.id,
            "url": session.url,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/audit", methods=["POST"])
def submit_audit():
    """Capture a free site audit request."""
    try:
        data = request.json or {}
        audit_log = Path(__file__).parent / "audit_requests.json"
        if not audit_log.exists():
            audit_log.write_text(json.dumps([], indent=2))
        entries = json.loads(audit_log.read_text())
        entries.append({
            "timestamp": datetime.now().isoformat(),
            "business": data.get("business", ""),
            "website": data.get("website", ""),
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "industry": data.get("industry", ""),
            "status": "new",
        })
        audit_log.write_text(json.dumps(entries, indent=2))
        print(f"[audit] New request from {data.get('business', 'unknown')}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events (payment_intent.succeeded, charge.completed)."""
    sig_header = request.headers.get("stripe-signature")
    
    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            request.data,
            sig_header,
            STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400
    
    # Handle payment/subscription events
    if event["type"] in ("checkout.session.completed", "invoice.paid"):
        session = event["data"]["object"]
        payment_intent = session.payment_intent
        
        # Extract customer info
        metadata = session.metadata or {}
        business_name = metadata.get("business_name", "Unknown")
        industry = metadata.get("industry", "local-business")
        email = metadata.get("email", session.customer_email or "")
        
        print(f"\n✅ Payment received from {business_name}")
        
        # Log the payment
        log_payment({
            "timestamp": datetime.now().isoformat(),
            "payment_id": payment_intent,
            "business_name": business_name,
            "industry": industry,
            "email": email,
            "amount_usd": session.amount_total / 100,
            "status": "completed"
        })
        
        # Build the website
        try:
            build_config = {
                "business_name": business_name,
                "industry": industry,
                "email": email,
                "tagline": f"Welcome to {business_name}",
                "phone": "",
                "address": "",
                "website": f"{business_name.lower().replace(' ', '')}.buildswift.site",
                "services": ["Learn more", "Contact us"],
                "hours": "Contact for details",
                "description": f"Professional website for {business_name}"
            }
            
            build_dir, cost = build_site(build_config)
            print(f"✅ Website built: {build_dir}")
            
            # Deploy to customer domain
            deploy_site(business_name, build_dir)
            
            # Update log with build status
            update_payment_log(payment_intent, {"build_dir": build_dir, "deploy_status": "completed"})
            
        except Exception as e:
            print(f"❌ Build failed: {e}")
            update_payment_log(payment_intent, {"build_status": "failed", "error": str(e)})
    
    return jsonify({"ok": True}), 200


def log_payment(payment_data):
    """Log payment to JSON file."""
    logs = json.loads(PAYMENT_LOG.read_text())
    logs.append(payment_data)
    PAYMENT_LOG.write_text(json.dumps(logs, indent=2))


def update_payment_log(payment_id, updates):
    """Update an existing payment entry."""
    logs = json.loads(PAYMENT_LOG.read_text())
    for entry in logs:
        if entry.get("payment_id") == payment_id:
            entry.update(updates)
            break
    PAYMENT_LOG.write_text(json.dumps(logs, indent=2))


def deploy_site(business_name, build_dir):
    """
    Deploy built site to customer domain.
    Placeholder: In production, this would:
    1. Update DNS/subdomain routing
    2. Deploy to CDN/hosting (Vercel, Netlify, S3+CloudFront, etc.)
    3. Set up SSL certificate
    4. Configure email forwarding
    """
    slug = business_name.lower().replace(" ", "-").replace("'", "")
    domain = f"{slug}.buildswift.site"
    
    print(f"🚀 Deploying {business_name} to {domain}")
    print(f"   Build directory: {build_dir}")
    
    # For now, log deployment info
    deploy_info = {
        "business": business_name,
        "domain": domain,
        "build_dir": build_dir,
        "deployed_at": datetime.now().isoformat(),
        "status": "deployed"
    }
    
    # Create deployments log
    deployments_log = Path(__file__).parent / "deployments.json"
    if not deployments_log.exists():
        deployments_log.write_text(json.dumps([], indent=2))
    
    logs = json.loads(deployments_log.read_text())
    logs.append(deploy_info)
    deployments_log.write_text(json.dumps(logs, indent=2))
    
    print(f"✅ Deployment logged: {domain}")


@app.route("/success", methods=["GET"])
def success():
    """Payment success page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Successful - BuildSwift</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f0f0; }
            h1 { color: #28a745; }
            p { color: #333; font-size: 18px; }
            a { color: #007bff; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>✅ Payment Received!</h1>
        <p>Your website is being built right now. We'll send you an email when it's ready.</p>
        <p><a href="/">← Back to BuildSwift</a></p>
    </body>
    </html>
    """


@app.route("/cancel", methods=["GET"])
def cancel():
    """Payment cancelled page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Cancelled - BuildSwift</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f0f0; }
            h1 { color: #dc3545; }
            a { color: #007bff; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>Payment Cancelled</h1>
        <p><a href="/">← Try Again</a></p>
    </body>
    </html>
    """


@app.route("/api/payments", methods=["GET"])
def list_payments():
    """List all payments (admin only)."""
    # TODO: Add auth check
    logs = json.loads(PAYMENT_LOG.read_text())
    return jsonify(logs)


@app.route("/api/deployments", methods=["GET"])
def list_deployments():
    """List all deployments (admin only)."""
    # TODO: Add auth check
    deployments_log = Path(__file__).parent / "deployments.json"
    if deployments_log.exists():
        logs = json.loads(deployments_log.read_text())
        return jsonify(logs)
    return jsonify([])


# ============================================================================
# Meta Social Media Posting Endpoints (Facebook & Instagram Integration)
# ============================================================================

@app.route("/meta/fb/post", methods=["POST"])
def post_to_facebook():
    """
    Publish a post to Facebook page.
    
    Required JSON payload:
    {
        "page_id": "FACEBOOK_PAGE_ID",
        "message": "Post content",
        "access_token": "PAGE_ACCESS_TOKEN"
    }
    
    Returns: Facebook post ID on success
    """
    try:
        data = request.get_json() or {}
        page_id = data.get("page_id")
        message = data.get("message")
        access_token = data.get("access_token")
        
        if not all([page_id, message, access_token]):
            return jsonify({
                "error": "Missing required fields: page_id, message, access_token"
            }), 400
        
        # Call Facebook Graph API
        fb_api_url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
        response = requests.post(fb_api_url, data={
            "message": message,
            "access_token": access_token
        })
        
        result = response.json()
        
        if "error" in result:
            return jsonify({
                "error": f"Facebook API error: {result['error']['message']}"
            }), 400
        
        # Log the social post
        log_social_post({
            "timestamp": datetime.now().isoformat(),
            "platform": "facebook",
            "page_id": page_id,
            "post_id": result.get("id"),
            "message_preview": message[:100],
            "status": "published"
        })
        
        return jsonify({
            "status": "published",
            "post_id": result.get("id"),
            "platform": "facebook",
            "message": "Post published successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/meta/ig/post", methods=["POST"])
def post_to_instagram():
    """
    Publish a post to Instagram account.
    
    Required JSON payload:
    {
        "ig_account_id": "INSTAGRAM_ACCOUNT_ID",
        "image_url": "URL_TO_IMAGE",
        "caption": "Post caption",
        "access_token": "USER_ACCESS_TOKEN"
    }
    
    Returns: Instagram media ID on success
    """
    try:
        data = request.get_json() or {}
        ig_account_id = data.get("ig_account_id")
        image_url = data.get("image_url")
        caption = data.get("caption")
        access_token = data.get("access_token")
        
        if not all([ig_account_id, image_url, caption, access_token]):
            return jsonify({
                "error": "Missing required fields: ig_account_id, image_url, caption, access_token"
            }), 400
        
        # First, create media object
        ig_api_url = f"https://graph.instagram.com/v19.0/{ig_account_id}/media"
        response = requests.post(ig_api_url, data={
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token
        })
        
        result = response.json()
        
        if "error" in result:
            return jsonify({
                "error": f"Instagram API error: {result['error']['message']}"
            }), 400
        
        media_id = result.get("id")
        
        # Publish the media
        publish_url = f"https://graph.instagram.com/v19.0/{media_id}/publish"
        publish_response = requests.post(publish_url, data={
            "access_token": access_token
        })
        
        publish_result = publish_response.json()
        
        if "error" in publish_result:
            return jsonify({
                "error": f"Instagram publish error: {publish_result['error']['message']}"
            }), 400
        
        # Log the social post
        log_social_post({
            "timestamp": datetime.now().isoformat(),
            "platform": "instagram",
            "ig_account_id": ig_account_id,
            "media_id": media_id,
            "caption_preview": caption[:100],
            "status": "published"
        })
        
        return jsonify({
            "status": "published",
            "media_id": media_id,
            "platform": "instagram",
            "message": "Post published successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/meta/x/post", methods=["POST"])
def post_to_x():
    """
    Publish a post to X (Twitter) using OAuth 1.0a.
    
    Required JSON payload:
    {
        "text": "Tweet content"
    }
    
    Optional:
    {
        "media_ids": ["media_id_1", "media_id_2"]
    }
    
    Returns: Tweet ID on success
    """
    try:
        from requests_oauthlib import OAuth1Session
        
        data = request.get_json() or {}
        text = data.get("text")
        media_ids = data.get("media_ids", [])
        
        if not text:
            return jsonify({
                "error": "Missing required field: text"
            }), 400
        
        # Try Bearer token first (app-only auth - might have write permissions)
        bearer_token = os.environ.get("X_BEARER_TOKEN")
        
        if bearer_token:
            # Try v2 API with Bearer token
            x_api_url = "https://api.twitter.com/2/tweets"
            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json"
            }
            
            payload = {"text": text}
            if media_ids:
                payload["media"] = {"media_ids": media_ids}
            
            response = requests.post(x_api_url, json=payload, headers=headers)
            result = response.json()
            
            print(f"X API (Bearer) Response Status: {response.status_code}")
            print(f"X API (Bearer) Response: {result}")
            
            if response.status_code == 200:
                tweet_id = result.get("data", {}).get("id")
                # Log and return success
                log_social_post({
                    "timestamp": datetime.now().isoformat(),
                    "platform": "x",
                    "tweet_id": tweet_id,
                    "text_preview": text[:100],
                    "status": "published"
                })
                return jsonify({
                    "status": "published",
                    "tweet_id": tweet_id,
                    "platform": "x",
                    "message": "Tweet posted successfully"
                }), 200
            elif response.status_code == 403 and "Unsupported Authentication" in str(result):
                print("Bearer token doesn't support v2 tweets endpoint, trying OAuth 1.0a...")
            else:
                # Different error
                error_msg = result.get("errors", [result.get("error", {})]).get("message", "Unknown error")
                return jsonify({
                    "error": f"X API error: {error_msg}",
                    "status_code": response.status_code
                }), 400
        
        # Fallback to OAuth 1.0a
        client_key = os.environ.get("X_CONSUMER_KEY")
        client_secret = os.environ.get("X_CONSUMER_SECRET")
        resource_owner_key = os.environ.get("X_ACCESS_TOKEN")
        resource_owner_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")
        
        if not all([client_key, client_secret, resource_owner_key, resource_owner_secret]):
            return jsonify({
                "error": "Missing X OAuth 1.0a credentials in environment"
            }), 400
        
        # Create OAuth 1.0a session
        oauth = OAuth1Session(
            client_key,
            client_secret=client_secret,
            resource_owner_key=resource_owner_key,
            resource_owner_secret=resource_owner_secret
        )
        
        # Call X API v1.1 (POST statuses/update endpoint)
        x_api_url = "https://api.twitter.com/1.1/statuses/update.json"
        
        payload = {"status": text}
        if media_ids:
            payload["media_ids"] = ",".join(media_ids)
        
        response = oauth.post(x_api_url, data=payload)
        result = response.json()
        
        print(f"X API (OAuth1.0a) Response Status: {response.status_code}")
        print(f"X API (OAuth1.0a) Response: {result}")
        
        if response.status_code != 200:
            error_msg = result.get("errors", [{}])[0].get("message", "Unknown error")
            return jsonify({
                "error": f"X API error: {error_msg}",
                "status_code": response.status_code,
                "raw_response": result
            }), 400
        
        tweet_id = result.get("id_str")
        
        # Log the post
        log_social_post({
            "timestamp": datetime.now().isoformat(),
            "platform": "x",
            "tweet_id": tweet_id,
            "text_preview": text[:100],
            "status": "published"
        })
        
        return jsonify({
            "status": "published",
            "tweet_id": tweet_id,
            "platform": "x",
            "message": "Tweet posted successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/meta/youtube/upload", methods=["POST"])
def upload_to_youtube():
    """
    Upload a video to YouTube using YouTube Data API v3.
    
    Required JSON payload:
    {
        "title": "Video title",
        "description": "Video description (optional)",
        "video_url": "URL to video file or local path",
        "privacy_status": "public|unlisted|private (optional, default: public)"
    }
    
    Optional:
    {
        "access_token": "YOUTUBE_ACCESS_TOKEN (uses env by default)"
    }
    
    Returns: Video ID on success
    """
    try:
        data = request.get_json() or {}
        title = data.get("title")
        description = data.get("description", "")
        video_url = data.get("video_url")
        access_token = data.get("access_token") or os.environ.get("YOUTUBE_ACCESS_TOKEN")
        privacy_status = data.get("privacy_status", "public")
        
        if not all([title, video_url]):
            return jsonify({
                "error": "Missing required fields: title, video_url"
            }), 400
        
        if not access_token:
            return jsonify({
                "error": "Missing YouTube access token. Set YOUTUBE_ACCESS_TOKEN in environment or pass in request."
            }), 400
        
        # YouTube upload via Google API
        youtube_api_url = "https://www.googleapis.com/youtube/v3/videos?part=snippet,status"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "snippet": {
                "title": title,
                "description": description
            },
            "status": {
                "privacyStatus": privacy_status
            }
        }
        
        # Note: This is simplified. Real implementation needs multipart/form-data for video file
        response = requests.post(youtube_api_url, json=payload, headers=headers)
        result = response.json()
        
        if "error" in result:
            return jsonify({
                "error": f"YouTube API error: {result['error'].get('message', 'Unknown')}"
            }), 400
        
        video_id = result.get("id")
        
        log_social_post({
            "timestamp": datetime.now().isoformat(),
            "platform": "youtube",
            "video_id": video_id,
            "title": title[:100],
            "status": "uploaded"
        })
        
        return jsonify({
            "status": "uploaded",
            "video_id": video_id,
            "platform": "youtube",
            "message": "Video uploaded successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/meta/tiktok/post", methods=["POST"])
def post_to_tiktok():
    """
    Publish a video to TikTok using Content Posting API.
    
    Required JSON payload:
    {
        "video_url": "URL to video file or local path",
        "caption": "Video caption",
        "access_token": "TIKTOK_USER_ACCESS_TOKEN (optional - can be passed in request)"
    }
    
    Optional:
    {
        "hashtags": ["tag1", "tag2"],
        "disable_comment": false,
        "disable_duet": false,
        "disable_stitch": false
    }
    
    Returns: Video ID on success
    Note: Requires user access token from TikTok OAuth. This endpoint prepares the POST request.
    """
    try:
        data = request.get_json() or {}
        video_url = data.get("video_url")
        caption = data.get("caption")
        access_token = data.get("access_token") or os.environ.get("TIKTOK_USER_ACCESS_TOKEN")
        hashtags = data.get("hashtags", [])
        
        if not all([video_url, caption]):
            return jsonify({
                "error": "Missing required fields: video_url, caption"
            }), 400
        
        # Get client credentials from environment
        client_key = os.environ.get("TIKTOK_CLIENT_KEY")
        client_secret = os.environ.get("TIKTOK_CLIENT_SECRET")
        
        if not client_key or not client_secret:
            return jsonify({
                "error": "TikTok client credentials not configured (TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET)"
            }), 400
        
        # Check if user access token is available
        if not access_token:
            return jsonify({
                "status": "ready",
                "platform": "tiktok",
                "message": "TikTok endpoint configured. Requires user OAuth access token to post.",
                "note": "Pass access_token in request body or set TIKTOK_USER_ACCESS_TOKEN in environment",
                "client_key_configured": bool(client_key),
                "client_secret_configured": bool(client_secret)
            }), 200
        
        # TikTok Content Posting API - Initialize upload
        tiktok_api_url = "https://open.tiktok.com/v1/video/upload/init/"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Build caption with hashtags
        full_caption = caption
        if hashtags:
            full_caption += " " + " ".join([f"#{tag}" for tag in hashtags])
        
        payload = {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": 0  # Would be actual size
            },
            "post_info": {
                "title": full_caption[:150],
                "privacy_level": "PUBLIC_TO_ANYONE"
            }
        }
        
        try:
            response = requests.post(tiktok_api_url, json=payload, headers=headers, timeout=10)
            result = response.json()
            
            if response.status_code != 200:
                error_msg = result.get("error", {}).get("message", "Unknown error")
                return jsonify({
                    "error": f"TikTok API error: {error_msg}",
                    "status_code": response.status_code
                }), 400
            
            upload_id = result.get("data", {}).get("upload_id")
            
            log_social_post({
                "timestamp": datetime.now().isoformat(),
                "platform": "tiktok",
                "upload_id": upload_id,
                "caption_preview": caption[:100],
                "status": "initiated"
            })
            
            return jsonify({
                "status": "initiated",
                "upload_id": upload_id,
                "platform": "tiktok",
                "message": "TikTok upload initiated"
            }), 200
        except requests.exceptions.RequestException as req_err:
            return jsonify({
                "error": f"TikTok API request failed: {str(req_err)}"
            }), 503
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def log_social_post(post_data):
    """Log social media post to JSON file."""
    social_log = Path(__file__).parent / "social_posts.json"
    if not social_log.exists():
        social_log.write_text(json.dumps([], indent=2))
    
    logs = json.loads(social_log.read_text())
    logs.append(post_data)
    social_log.write_text(json.dumps(logs, indent=2))


# MARK: - Enhanced Social Dashboard API Endpoints

@app.route("/meta/status", methods=["GET"])
def meta_status():
    """Check API connection status."""
    return jsonify({
        "status": "connected",
        "server": "buildswift",
        "timestamp": datetime.now().isoformat(),
        "platforms": ["facebook", "instagram", "x", "youtube", "tiktok"]
    }), 200


@app.route("/meta/posts", methods=["GET"])
def meta_posts():
    """Get recent social media posts."""
    social_log = Path(__file__).parent / "social_posts.json"
    if not social_log.exists():
        return jsonify([]), 200
    
    posts = json.loads(social_log.read_text())
    # Return formatted posts with engagement metrics
    formatted = []
    for post in posts[-20:]:  # Last 20 posts
        formatted.append({
            "id": post.get("post_id", post.get("upload_id", f"post_{len(formatted)}")),
            "platform": post.get("platform", "unknown"),
            "content": post.get("caption_preview", ""),
            "imageURL": None,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "timestamp": post.get("timestamp", datetime.now().isoformat())
        })
    return jsonify(formatted), 200


@app.route("/meta/analytics", methods=["GET"])
def meta_analytics():
    """Get platform analytics, filtered by brand."""
    brand = request.args.get("brand", "combined").lower()  # combined, urban_kayaks, taco_rio
    print(f"[DEBUG] meta_analytics called with brand={brand}")
    print(f"[DEBUG] ANALYTICS_DATA keys: {list(ANALYTICS_DATA.keys())}")
    
    if brand == "combined":
        # Merge both brands' data for all platforms that exist in either
        analytics = {}
        all_platforms = set(
            list(ANALYTICS_DATA.get("urban_kayaks", {}).keys()) + 
            list(ANALYTICS_DATA.get("taco_rio", {}).keys())
        )
        
        for platform in all_platforms:
            uk_data = ANALYTICS_DATA.get("urban_kayaks", {}).get(platform)
            tr_data = ANALYTICS_DATA.get("taco_rio", {}).get(platform)
            
            # Only include if at least one brand has it
            if uk_data or tr_data:
                uk_followers = uk_data.get("followers", 0) if uk_data else 0
                tr_followers = tr_data.get("followers", 0) if tr_data else 0
                uk_engagement = uk_data.get("engagement", 0) if uk_data else 0
                tr_engagement = tr_data.get("engagement", 0) if tr_data else 0
                uk_reach = uk_data.get("reach", 0) if uk_data else 0
                tr_reach = tr_data.get("reach", 0) if tr_data else 0
                uk_impressions = uk_data.get("impressions", 0) if uk_data else 0
                tr_impressions = tr_data.get("impressions", 0) if tr_data else 0
                uk_change = uk_data.get("reachChange", 0) if uk_data else 0
                tr_change = tr_data.get("reachChange", 0) if tr_data else 0
                
                # Count how many brands have this platform
                brand_count = sum([1 for d in [uk_data, tr_data] if d])
                
                analytics[platform] = {
                    "platform": platform,
                    "followers": uk_followers + tr_followers,
                    "engagement": (uk_engagement + tr_engagement) / brand_count if brand_count > 0 else 0,
                    "reach": uk_reach + tr_reach,
                    "impressions": uk_impressions + tr_impressions,
                    "reachChange": (uk_change + tr_change) / brand_count if brand_count > 0 else 0
                }
    elif brand in ANALYTICS_DATA:
        # Return only platforms that this brand has
        analytics = dict(ANALYTICS_DATA[brand])
    else:
        return jsonify({"error": f"Unknown brand: {brand}"}), 400
    
    return jsonify(analytics), 200


@app.route("/meta/feed", methods=["GET"])
def meta_feed():
    """Get engagement feed (mentions, comments, likes)."""
    feed = [
        {
            "id": "feed_1",
            "platform": "Instagram",
            "author": "@kayak_lover_chi",
            "content": "This looks amazing! When do you open for the season?",
            "type": "comment",
            "timestamp": datetime.now().isoformat(),
            "action": "replied"
        },
        {
            "id": "feed_2",
            "platform": "Facebook",
            "author": "Sarah M.",
            "content": "Had a great time last summer!",
            "type": "review",
            "timestamp": datetime.now().isoformat(),
            "action": "liked"
        },
        {
            "id": "feed_3",
            "platform": "X",
            "author": "@chi_events",
            "content": "Check out @urbankayaks for team building!",
            "type": "mention",
            "timestamp": datetime.now().isoformat(),
            "action": "retweeted"
        }
    ]
    return jsonify(feed), 200


@app.route("/meta/dms", methods=["GET"])
def meta_dms():
    """Get direct message queue."""
    dms = [
        {
            "id": "dm_1",
            "platform": "Instagram",
            "sender": "@corporate_events",
            "message": "Hi, we'd like to book a group of 20 people. Can you help?",
            "timestamp": datetime.now().isoformat(),
            "priority": 3,
            "replied": False
        },
        {
            "id": "dm_2",
            "platform": "Facebook",
            "sender": "Mike Johnson",
            "message": "What's your cancellation policy?",
            "timestamp": datetime.now().isoformat(),
            "priority": 2,
            "replied": False
        }
    ]
    return jsonify(dms), 200


@app.route("/meta/scheduled", methods=["GET"])
def meta_scheduled():
    """Get scheduled posts."""
    scheduled_log = Path(__file__).parent / "scheduled_posts.json"
    if not scheduled_log.exists():
        return jsonify([]), 200
    
    scheduled = json.loads(scheduled_log.read_text())
    return jsonify(scheduled), 200


@app.route("/meta/schedule", methods=["POST"])
def meta_schedule():
    """Schedule a post for later."""
    try:
        data = request.json
        scheduled_log = Path(__file__).parent / "scheduled_posts.json"
        
        if not scheduled_log.exists():
            scheduled_log.write_text(json.dumps([], indent=2))
        
        scheduled = json.loads(scheduled_log.read_text())
        scheduled.append({
            "id": data.get("id"),
            "platforms": data.get("platforms", []),
            "content": data.get("content", ""),
            "mediaURL": data.get("mediaURL"),
            "scheduledFor": data.get("scheduledFor"),
            "status": "scheduled",
            "createdAt": datetime.now().isoformat()
        })
        
        scheduled_log.write_text(json.dumps(scheduled, indent=2))
        
        return jsonify({
            "status": "scheduled",
            "postID": data.get("id"),
            "platforms": len(data.get("platforms", [])),
            "scheduledFor": data.get("scheduledFor")
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/meta/scheduled/<post_id>", methods=["DELETE"])
def meta_delete_scheduled(post_id):
    """Delete a scheduled post."""
    try:
        scheduled_log = Path(__file__).parent / "scheduled_posts.json"
        if not scheduled_log.exists():
            return jsonify({"error": "No scheduled posts found"}), 404
        
        scheduled = json.loads(scheduled_log.read_text())
        scheduled = [p for p in scheduled if p.get("id") != post_id]
        scheduled_log.write_text(json.dumps(scheduled, indent=2))
        
        return jsonify({"status": "deleted", "postID": post_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/meta/dms/<dm_id>/reply", methods=["POST"])
def meta_reply_dm(dm_id):
    """Reply to a direct message."""
    try:
        data = request.json
        reply_text = data.get("reply", "")
        
        # Log reply
        log_social_post({
            "timestamp": datetime.now().isoformat(),
            "platform": "dm_reply",
            "dm_id": dm_id,
            "reply": reply_text,
            "status": "sent"
        })
        
        return jsonify({
            "status": "replied",
            "dmID": dm_id,
            "reply": reply_text
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/meta/auto-reply", methods=["POST"])
def meta_auto_reply():
    """Set up auto-reply rules."""
    try:
        data = request.json
        auto_reply_log = Path(__file__).parent / "auto_replies.json"
        
        if not auto_reply_log.exists():
            auto_reply_log.write_text(json.dumps([], indent=2))
        
        rules = json.loads(auto_reply_log.read_text())
        rules.append({
            "platform": data.get("platform"),
            "keyword": data.get("keyword"),
            "reply": data.get("reply"),
            "enabled": data.get("enabled", True),
            "createdAt": datetime.now().isoformat()
        })
        
        auto_reply_log.write_text(json.dumps(rules, indent=2))
        
        return jsonify({
            "status": "created",
            "platform": data.get("platform"),
            "keyword": data.get("keyword")
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    print("\n" + "="*60)
    print("BuildSwift Payment Server Starting")
    print("="*60)
    print(f"Stripe Key: {STRIPE_PUBLISHABLE_KEY[:20]}...")
    print(f"Webhook Endpoint: /webhook")
    print(f"API Endpoint: /api/checkout")
    print("="*60 + "\n")
    
    app.run(host="0.0.0.0", port=5001, debug=False)
