# 🏛️ Google Sign-On Setup Guide

To enable Google authentication for your Finance Identity Framework, follow these exact steps in the Google Cloud Console.

## 1. Create a Google Cloud Project
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown at the top and select **New Project**.
3. Name it `Vault-Protocol-Finance` and click **Create**.

## 2. Configure OAuth Consent Screen
1. In the left sidebar, go to **APIs & Services** > **OAuth consent screen**.
2. Select **External** (if you don't have a Google Workspace) and click **Create**.
3. Fill in the required fields:
   - **App name:** `Vault Protocol`
   - **User support email:** (Your email)
   - **Developer contact info:** (Your email)
4. Click **Save and Continue** through the next screens (Scopes and Test Users).
   - *Note: In "Test Users", add your Gmail/Institutional emails to ensure they can log in while the app is in testing mode.*

## 3. Create OAuth 2.0 Credentials
1. Go to **APIs & Services** > **Credentials**.
2. Click **+ Create Credentials** > **OAuth client ID**.
3. **Application type:** Web application.
4. **Name:** `Vault Finance Web Client`.
5. **Authorized redirect URIs:**
   - Click **Add URI** and enter: 
     `http://127.0.0.1:5002/login/google/callback`
     *(Note: If you use `localhost` instead of `127.0.0.1`, add `http://localhost:5002/login/google/callback` as well)*.
6. Click **Create**.

## 4. Finalize Configuration
1. A dialog will appear with your **Client ID** and **Client Secret**.
2. Copy these values and paste them into your `.env` file:
   ```env
   FIN_GOOGLE_CLIENT_ID=your_id_here
   FIN_GOOGLE_CLIENT_SECRET=your_secret_here
   ```
3. **Restart the server** to apply the changes.

## 5. Role Mapping (Pre-Configured)
The application is configured to automatically recognize these emails:
- `25177@yenepoya.edu.in` → **Admin**
- `raihanaanzar2@gmail.com` → **Analyst**
- `raihanaanzar@gmail.com` → **Auditor**
