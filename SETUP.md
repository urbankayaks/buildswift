# BuildSwift Setup Guide

## Prerequisites
- Python 3.8+
- pip
- Stripe CLI (installed ✅)
- A Stripe account (free to create)

## Step 1: Create Stripe Account & Get API Keys

### Option A: Create New Stripe Account
1. Go to https://dashboard.stripe.com/register
2. Sign up with your email (preferably buildswift@company.com or similar)
3. Follow verification steps
4. Go to Settings → API Keys (https://dashboard.stripe.com/apikeys)
5. Copy your **Publishable Key** (pk_live_...)
6. Copy your **Secret Key** (sk_live_...)

### Option B: Use Test Keys (Recommended for Testing)
If you want to test before going live:
1. On API Keys page, toggle "Viewing test data" at top
2. Use the test **Publishable Key** (pk_test_...)
3. Use the test **Secret Key** (sk_test_...)

## Step 2: Set Up Webhook Endpoint

Stripe needs to know where to send payment confirmation webhooks.

```bash
# For local testing with Stripe CLI:
stripe listen --forward-to localhost:5000/webhook

# This will output a webhook signing secret: whsec_...
# Save this!
```

## Step 3: Configure Environment

1. Copy the example config:
```bash
cp .env.example .env
```

2. Edit `.env` and add your keys:
```
STRIPE_PUBLISHABLE_KEY=pk_live_YOUR_KEY
STRIPE_SECRET_KEY=sk_live_YOUR_KEY
STRIPE_WEBHOOK_SECRET=whsec_YOUR_KEY
```

## Step 4: Install Dependencies & Run

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set environment variables
export $(cat .env | xargs)

# Run the Flask server
python server.py
```

Server will start at `http://localhost:5000`

## Step 5: Test Payment Flow

1. Navigate to http://localhost:5000
2. Fill in business details
3. Click "Get Started"
4. Use Stripe test card: **4242 4242 4242 4242** (any future date, any CVC)
5. Check `/api/payments` to see payment logs
6. Check `deployments.json` to see generated sites

## Step 6: Deploy to Production

Once testing is complete:

1. Update `.env` with LIVE keys (pk_live_, sk_live_)
2. Deploy Flask server (Heroku, AWS, DigitalOcean, etc.)
3. Configure webhook endpoint in Stripe dashboard with production URL
4. Test with small amount to verify
5. Enable stripe_billing_notifications to email

## Stripe Test Cards

For testing different scenarios:

| Card Number | Expiry | CVC | Result |
|---|---|---|---|
| 4242 4242 4242 4242 | Any future | Any | Successful charge |
| 4000 0000 0000 0002 | Any future | Any | Declined (insufficient funds) |
| 4000 0000 0000 9995 | Any future | Any | Declined (lost card) |
| 378282246310005 | Any future | Any | Amex successful |

## Files Created

- `server.py` - Flask app with Stripe integration
- `pipeline/builder.py` - Website builder (uses MiniMax API)
- `requirements.txt` - Python dependencies
- `.env` - Configuration (create from .env.example)
- `payments.json` - Payment log (auto-created)
- `deployments.json` - Deployment log (auto-created)
- `builds/` - Directory containing built websites

## API Endpoints

### POST /api/checkout
Create a checkout session.
```json
{
  "business_name": "Joe's Pizza",
  "industry": "restaurant",
  "email": "joe@example.com"
}
```

### POST /webhook
Stripe webhook endpoint for payment events.

### GET /api/payments
List all payments (admin endpoint).

### GET /api/deployments
List all deployments (admin endpoint).

### GET /success
Payment success page.

### GET /cancel
Payment cancel page.

## Troubleshooting

### "STRIPE_WEBHOOK_SECRET is empty"
- You need to set up `stripe listen` or configure in Stripe dashboard
- Get the secret from the output of `stripe listen --forward-to localhost:5000/webhook`

### "MiniMax API failed"
- Check that MINIMAX_API_KEY is set in .env
- Verify the key is valid (check account at minimax.io)

### Payment webhook not triggering
- Make sure Stripe CLI is running: `stripe listen --forward-to localhost:5000/webhook`
- Or configure webhook in Stripe dashboard (Settings → Webhooks)

### Port 5000 already in use
- Change PORT in .env, or kill the process:
  ```bash
  lsof -ti:5000 | xargs kill -9
  ```

## Next Steps

1. ✅ Set up Stripe account & get keys
2. ✅ Configure webhook endpoint
3. ✅ Test payment flow with test cards
4. ✅ Generate sample websites to verify builder.py works
5. ✅ Deploy to production
6. ✅ Monitor payments and deployments

---

**Questions?** Check Stripe docs: https://docs.stripe.com/
