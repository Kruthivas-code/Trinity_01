# Gmail Push Notifications Setup Guide

## Overview
This guide will help you set up Gmail Push Notifications using Google Cloud Pub/Sub for real-time email ingestion into TickFlow.

**Time Required:** 15-20 minutes  
**Cost:** Free (within Google Cloud free tier limits)

---

## Prerequisites
- Google Account with access to support@emergent.sh
- Google Cloud Platform account (can use same Google account)
- Admin access to console.cloud.google.com

---

## Step 1: Create Google Cloud Project

1. Go to https://console.cloud.google.com
2. Click "Select a project" dropdown at the top
3. Click "NEW PROJECT"
4. Enter project details:
   - **Project name:** `TickFlow-Production`
   - **Organization:** (your organization)
   - **Location:** (your organization or No organization)
5. Click **CREATE**
6. Wait for project creation (~30 seconds)
7. **Copy your Project ID** - you'll need this later

---

## Step 2: Enable Required APIs

1. In the Google Cloud Console, go to **APIs & Services > Library**
2. Search for and enable these APIs (click ENABLE for each):
   - **Gmail API**
   - **Cloud Pub/Sub API**

---

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. If prompted to configure OAuth consent screen:
   - Click **CONFIGURE CONSENT SCREEN**
   - Choose **External** (or Internal if you have Google Workspace)
   - Fill in required fields:
     - **App name:** TickFlow
     - **User support email:** your@emergent.sh
     - **Developer contact:** your@emergent.sh
   - Click **SAVE AND CONTINUE**
   - On Scopes screen, click **SAVE AND CONTINUE** (we'll add scopes programmatically)
   - On Test users, add support@emergent.sh
   - Click **SAVE AND CONTINUE**
4. Now create OAuth client:
   - **Application type:** Web application
   - **Name:** TickFlow Production
   - **Authorized JavaScript origins:** 
     - `https://qa-finished.preview.emergentagent.com`
   - **Authorized redirect URIs:**
     - `https://qa-finished.preview.emergentagent.com/api/gmail/auth/callback`
5. Click **CREATE**
6. **SAVE THESE CREDENTIALS:**
   ```
   Client ID: [copy this - starts with numbers and ends with .apps.googleusercontent.com]
   Client Secret: [copy this - random string]
   ```
   You'll need these for environment variables.

---

## Step 4: Create Pub/Sub Topic

1. Go to **Pub/Sub > Topics** in the sidebar
2. Click **CREATE TOPIC**
3. Enter:
   - **Topic ID:** `gmail-push-notifications`
   - Leave other settings as default
4. Click **CREATE**
5. **Copy the full topic name:**
   ```
   projects/YOUR-PROJECT-ID/topics/gmail-push-notifications
   ```

---

## Step 5: Create Pub/Sub Subscription

1. In the Topics list, click on `gmail-push-notifications`
2. Click **CREATE SUBSCRIPTION** at the top
3. Enter:
   - **Subscription ID:** `tickflow-webhook`
   - **Delivery type:** Push
   - **Endpoint URL:** `https://qa-finished.preview.emergentagent.com/api/gmail/webhook`
   - **Acknowledgement deadline:** 60 seconds
4. Click **CREATE**

---

## Step 6: Grant Gmail Permission to Publish

1. In the Pub/Sub Topics page, click on `gmail-push-notifications`
2. Click **PERMISSIONS** tab
3. Click **ADD PRINCIPAL**
4. Enter:
   - **New principals:** `gmail-api-push@system.gserviceaccount.com`
   - **Role:** Pub/Sub Publisher
5. Click **SAVE**

---

## Step 7: Enable Gmail Push Notifications

**Important:** This step requires a Gmail API call. I'll provide you a curl command to run:

1. First, get an access token:
   ```bash
   # Install gcloud CLI if not already: https://cloud.google.com/sdk/docs/install
   gcloud auth application-default login
   gcloud auth application-default print-access-token
   ```
   **Copy the access token**

2. Run this curl command (replace YOUR_ACCESS_TOKEN and YOUR_PROJECT_ID):
   ```bash
   curl -X POST \
     "https://gmail.googleapis.com/gmail/v1/users/support@emergent.sh/watch" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "topicName": "projects/YOUR_PROJECT_ID/topics/gmail-push-notifications",
       "labelIds": ["INBOX"]
     }'
   ```

3. You should see a response like:
   ```json
   {
     "historyId": "123456",
     "expiration": "1234567890000"
   }
   ```

**Note:** Gmail watch expires after 7 days. TickFlow will automatically renew it, but save this command in case you need to manually trigger it.

---

## Step 8: Provide Credentials to TickFlow

Once you have all the credentials, you'll add them to TickFlow via settings:

**Credentials needed:**
- Google Client ID (from Step 3)
- Google Client Secret (from Step 3)
- Project ID (from Step 1)
- Pub/Sub Topic (from Step 4)
- Pub/Sub Subscription (from Step 5)

I'll add a settings page in TickFlow where you can securely enter these.

---

## Verification

After setup, we'll verify:
1. Send a test email to support@emergent.sh
2. Check TickFlow for new ticket (should appear within 1 second)
3. Check Google Cloud Pub/Sub metrics for message delivery

---

## Troubleshooting

**Push notifications not working?**
1. Check Pub/Sub subscription has correct endpoint URL
2. Verify gmail-api-push@system.gserviceaccount.com has Publisher role
3. Check Gmail watch is active (run the curl command from Step 7 again)
4. Check TickFlow webhook endpoint logs for errors

**OAuth not working?**
1. Verify redirect URI matches exactly (including https://)
2. Check OAuth consent screen is configured
3. Verify support@emergent.sh is added as test user

---

## Maintenance

- **Gmail watch renewal:** TickFlow auto-renews every 6 days
- **Token refresh:** TickFlow auto-refreshes access tokens
- **Monitoring:** Check Google Cloud Pub/Sub metrics dashboard

---

## Cost Estimate

**Free tier limits:**
- Gmail API: 1,000,000,000 quota units/day (sufficient for ~250,000 emails)
- Pub/Sub: First 10 GB/month free (sufficient for ~1M emails)

**Expected usage for 10,000 emails/month:**
- Cost: $0 (well within free tier)

---

## Security Notes

- OAuth tokens stored encrypted in MongoDB
- Webhook endpoint validates Pub/Sub message signatures
- Client secret never exposed to frontend
- Refresh tokens rotated automatically

---

## Next Steps

Once you've completed this setup, let me know and I'll:
1. Add the credentials input page to TickFlow settings
2. Test the OAuth flow
3. Verify push notifications are working
4. Send a test email to confirm end-to-end flow

Ready to build! 🚀
