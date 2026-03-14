# 🎯 Explosion Hunter v3.0 — Railway Deployment Guide

## What This Does
- **Auto-scans** 35+ stocks every 10 minutes during market hours
- **Email alerts** when any stock scores ≥ 70
- **Live dashboard** auto-refreshes — no manual clicks
- **Runs 24/7** on Railway for ~$5/month

---

## Setup Steps (15 minutes total)

### Step 1: Create Gmail App Password (3 min)

1. Go to https://myaccount.google.com/security
2. Enable **2-Step Verification** if not already on
3. Go to https://myaccount.google.com/apppasswords
4. Create a new App Password:
   - App name: `Explosion Hunter`
   - Click **Create**
5. Copy the 16-character password (looks like: `abcd efgh ijkl mnop`)
6. **Save this password** — you'll need it in Step 3

### Step 2: Deploy to Railway (5 min)

1. Go to https://railway.app and sign up (credit card required for $5/month plan)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
   - If you don't want GitHub: Click **"Empty Project"** → **"Add a Service"** → **"Deploy a Template"** and upload the files manually
3. Connect this repo or upload the 4 files:
   - `app.py`
   - `requirements.txt`
   - `Procfile`
   - `.python-version`
4. Railway will auto-detect and start deploying

### Step 3: Set Environment Variables (2 min)

In Railway dashboard → Your service → **Variables** tab → Add these:

| Variable | Value |
|---|---|
| `GMAIL_ADDRESS` | your-email@gmail.com |
| `GMAIL_APP_PASSWORD` | abcdefghijklmnop (the 16-char app password from Step 1) |
| `ALERT_TO_EMAIL` | your-email@gmail.com (where to receive alerts) |
| `SCAN_INTERVAL` | 10 (minutes between scans) |
| `ALERT_THRESHOLD` | 70 (minimum score to trigger email) |

### Step 4: Generate Domain (1 min)

1. In Railway → Your service → **Settings** tab
2. Click **"Generate Domain"**
3. You'll get a URL like: `explosion-hunter-production.up.railway.app`
4. Open it — your dashboard is live!

### Step 5: Test Email (1 min)

1. Open your dashboard URL
2. Expand **"📧 Email Alert Status"**
3. Click **"Send Test Email"**
4. Check your Gmail inbox

---

## How It Works

### During Market Hours (9:30 AM - 4:00 PM ET)
- Dashboard auto-refreshes every 10 minutes
- Scanner analyzes all stocks with 14 criteria
- If any stock scores ≥ 70, you get an email
- Emails are only sent for **NEW** triggers (not repeated)

### Outside Market Hours
- Scanner pauses automatically
- Dashboard shows last scan results
- No emails sent
- Resumes automatically next trading day

---

## Customization

### Change Watchlist
Edit the `DEFAULT_WATCHLIST` in `app.py`, or modify it directly in the dashboard's "Customize Watchlist" expander.

### Change Alert Threshold
Set `ALERT_THRESHOLD` environment variable in Railway (default: 70)

### Change Scan Interval
Set `SCAN_INTERVAL` environment variable in Railway (default: 10 minutes)

---

## Cost
- Railway Hobby: **$5/month** (includes $5 compute credit)
- Gmail: **Free**
- yfinance: **Free**
- **Total: ~$5/month**

---

## Troubleshooting

**App shows "Application Error"**
→ Check Railway logs (Dashboard → Your service → Logs)

**No emails received**
→ Check spam folder
→ Verify GMAIL_APP_PASSWORD is the 16-char app password, NOT your regular Gmail password
→ Make sure 2-Step Verification is enabled on your Google account

**Stocks missing from results**
→ yfinance rate limits. The retry logic handles most failures, but some tickers may occasionally be unavailable.
