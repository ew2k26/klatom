# ew² Payment System Setup Guide (Ko-fi)

## Overview

This guide walks you through setting up the payment system for ew² tokens using **Ko-fi** as the payment gateway and **Cloudflare Workers** as the backend.

### Architecture

```
User → Website (Ko-fi button) → Ko-fi Payment ($3 USD)
                                        ↓
                                Ko-fi Webhook
                                        ↓
                            Cloudflare Worker
                                        ↓
                        ┌───────────────┴───────────────┐
                        ↓                               ↓
                Generate Token                   Send Email
                        ↓                          (Resend)
                Store in Cloudflare KV
                        ↓
                User receives token via email
                        ↓
                User enters token in ew²
                        ↓
                Validate against Worker API
                        ↓
                Activate locally (HWID-locked)
```

### What You Need

1. **Ko-fi Account** - Free at https://ko-fi.com
2. **Cloudflare Account** - For Workers and KV storage
3. **Resend API Key** - For email delivery (optional, free tier available)
4. **Wrangler CLI** - Cloudflare's CLI tool

---

## Step 1: Create Ko-fi Account

1. Go to https://ko-fi.com and sign up (free)
2. Choose a username (e.g., `ew2` or `ew2licenses`)
3. Complete your profile

### Set Up Shop Product

1. Go to **Shop → Add Product**
2. Fill in:
   - **Product Name**: ew² License
   - **Price**: $3.00 USD
   - **Description**: Permanent license token for ew² Discord Username Checker
3. Save the product

### Get Webhook Token

1. Go to **Settings → API Keys**
2. Find **Webhook Token** (or create one)
3. Copy this token - you'll need it for the Worker

---

## Step 2: Set Up Cloudflare Worker

### Install Wrangler

```bash
npm install -g wrangler
```

### Login to Cloudflare

```bash
wrangler login
```

### Create KV Namespace

```bash
cd worker
wrangler kv:namespace create TOKENS
```

This will output an ID. Update `wrangler.toml` with this ID:

```toml
kv_namespaces = [
  { binding = "TOKENS", id = "YOUR_ACTUAL_KV_NAMESPACE_ID" }
]
```

### Set Environment Variables

```bash
wrangler secret put KOFI_WEBHOOK_TOKEN
# Enter your Ko-fi webhook token

wrangler secret put RESEND_API_KEY
# Enter your Resend API key (or leave blank to skip email)

wrangler secret put TOKEN_SECRET
# Enter a random 32-byte hex string (generate with: openssl rand -hex 32)
```

### Deploy Worker

```bash
cd worker
wrangler deploy
```

Note the deployed URL (e.g., `ew2-payment.your-subdomain.workers.dev`).

### Update Ko-fi Webhook URL

Go back to Ko-fi → **Settings → API Keys → Webhooks**

Set the webhook URL to:
```
https://ew2-payment.your-subdomain.workers.dev/webhook/kofi
```

---

## Step 3: Configure Website

Open `website/index.html` and update this value:

```javascript
var KOFI_USERNAME = "your_username"; // Your Ko-fi username
```

---

## Step 4: Deploy Website

```bash
npx wrangler pages deploy website --project-name=ew2 --branch=main
```

---

## Step 5: Test the Flow

1. Open the website
2. Click "Buy License"
3. Complete the test payment on Ko-fi
4. Check that you receive the email with the token
5. Open ew² and enter the token
6. Verify activation succeeds

---

## Token Format

Tokens follow this format: `EW2-XXXXXXXX-XXXXXXXX-XXXXXXXX`

- `EW2-` prefix
- 3 groups of 8 hex characters
- Example: `EW2-A1B2C3D4-E5F6A7B8-C9D0E1F2`

---

## Security Notes

- **Webhook Verification**: Ko-fi webhooks are verified using a shared token
- **Token Storage**: Tokens are stored as SHA-256 hashes in Cloudflare KV
- **HWID Binding**: Tokens are locked to the machine after first activation
- **No Secrets in Frontend**: All API keys are stored as Cloudflare Worker secrets
- **HTTPS Only**: All communication uses encrypted connections

---

## Troubleshooting

### Webhook Not Receiving

1. Check the webhook URL in Ko-fi settings
2. Verify the Worker is deployed: `wrangler tail`
3. Check Ko-fi's webhook logs for errors

### Email Not Sending

1. Verify Resend API key is set: `wrangler secret list`
2. Check the Worker logs for email errors
3. Verify the sender email is authorized in Resend

### Token Validation Failing

1. Check the Worker is responding: `curl https://your-worker.workers.dev/`
2. Verify the token format is correct (EW2-XXXXXXXX-XXXXXXXX-XXXXXXXX)
3. Check Worker logs for validation errors

---

## Costs

- **Cloudflare Workers**: Free tier includes 100,000 requests/day
- **Cloudflare KV**: Free tier includes 100,000 reads/day, 1,000 writes/day
- **Resend**: Free tier includes 100 emails/day
- **Ko-fi**: Free (no monthly fees, no commission on donations)

---

## Support

For issues with this setup, contact via Discord: https://discord.gg/7FXYFJAYsz
