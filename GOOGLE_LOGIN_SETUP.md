# Google Login Setup for MauryaHub

This project now supports Google login for:

- user resource submissions
- user "My Submissions" dashboard
- admin approval/rejection workflow

Google login will not work until you add Google OAuth credentials in both:

- Google Cloud Console
- Render environment variables

## 1. Create a Google Cloud project

1. Open Google Cloud Console.
2. Create a new project, or select an existing one.
3. Make sure that project is selected in the top bar.

## 2. Configure the OAuth consent screen

In Google Cloud Console:

1. Open `Google Auth Platform` or `APIs & Services`.
2. Open `OAuth consent screen`.
3. Fill these basic details:
   - App name: `MauryaHub`
   - User support email: your Gmail
   - Audience: `External`
   - Developer contact email: your Gmail
4. Save/Finish the consent screen setup.

Notes:

- For personal testing, `External` is usually fine.
- If Google asks for test users, add the Gmail accounts you want to use while testing.

## 3. Create the OAuth client

In Google Cloud Console:

1. Open `Google Auth Platform > Clients`
   or `APIs & Services > Credentials`
2. Click `Create client`
   or `Create Credentials > OAuth client ID`
3. Choose `Web application`
4. Name it something like:
   `MauryaHub Web Login`

### Authorized JavaScript origins

Add these origins:

```text
http://127.0.0.1:5000
https://YOUR-RENDER-DOMAIN.onrender.com
```

Example:

```text
https://mauryahub.onrender.com
```

### Authorized redirect URIs

Add these redirect URLs:

```text
http://127.0.0.1:5000/auth/google/callback
https://YOUR-RENDER-DOMAIN.onrender.com/auth/google/callback
```

Example:

```text
https://mauryahub.onrender.com/auth/google/callback
```

5. Click `Create`
6. Copy both values:
   - `Client ID`
   - `Client Secret`

Keep these safe.

## 4. Add environment variables in Render

In Render Dashboard:

1. Open your web service
2. Open `Environment`
3. Add these environment variables

```env
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://YOUR-RENDER-DOMAIN.onrender.com/auth/google/callback
ADMIN_EMAILS=your-admin-email@gmail.com
```

Example:

```env
GOOGLE_CLIENT_ID=1234567890-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=https://mauryahub.onrender.com/auth/google/callback
ADMIN_EMAILS=yourname@gmail.com
```

If you want multiple admin emails:

```env
ADMIN_EMAILS=admin1@gmail.com,admin2@gmail.com
```

After adding them:

1. Click save
2. Choose `Save, rebuild, and deploy`

## 5. Local testing setup

If you want Google login to work locally too, set these locally before starting the app:

```env
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:5000/auth/google/callback
ADMIN_EMAILS=your-admin-email@gmail.com
```

You can keep them in a local `.env` file if you use one, but do not commit that file.

## 6. How admin access works now

This app currently supports two admin paths:

- old admin password login
- Google login with email listed in `ADMIN_EMAILS`

If your Google email is inside `ADMIN_EMAILS`, then after Google login:

- your user record gets role `admin`
- admin screens become available
- you can approve/reject resource submissions

## 7. Submission flow after setup

Once Google login is configured:

1. User logs in with Google
2. User opens `Submit Resource`
3. Resource goes into `pending_general_resources`
4. Admin opens `Pending Resources`
5. Admin approves or rejects
6. Approved resources go into `general_resources`
7. User can track status in `My Submissions`

## 8. Quick test checklist

After deploy, test in this order:

1. Open `/resources`
2. Click `Login`
3. Complete Google sign-in
4. Confirm login succeeds
5. Submit one test resource from a normal user account
6. Login with admin account
7. Open pending submissions page
8. Approve the resource
9. Confirm it appears on public resources page
10. Submit one more and reject it with a reason
11. Confirm that reason appears in user `My Submissions`

## 9. Common problems

### Error: `Google login is not configured yet`

Cause:

- `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` is missing in Render

Fix:

- add both env vars in Render
- redeploy

### Error: `redirect_uri_mismatch`

Cause:

- redirect URL in Google Cloud does not exactly match your app URL

Fix:

- make sure this value matches exactly:

```text
https://YOUR-RENDER-DOMAIN.onrender.com/auth/google/callback
```

### Login works locally but not on Render

Cause:

- local redirect URI and production redirect URI are different

Fix:

- add both URIs in Google Cloud
- set `GOOGLE_REDIRECT_URI` in Render to the Render URL only

### Logged in user is not admin

Cause:

- that email is not in `ADMIN_EMAILS`

Fix:

- add the exact Gmail address to `ADMIN_EMAILS`
- redeploy
- logout and login again

## 10. Files involved in this feature

Main backend:

- [app.py](/C:/MY_PROJECTS/MauryaHub/MauryaHub/app.py:1303)

Main templates:

- [resources.html](/C:/MY_PROJECTS/MauryaHub/MauryaHub/templates/resources.html:551)
- [submit_general_resource.html](/C:/MY_PROJECTS/MauryaHub/MauryaHub/templates/submit_general_resource.html:1)
- [my_resource_submissions.html](/C:/MY_PROJECTS/MauryaHub/MauryaHub/templates/my_resource_submissions.html:1)
- [admin_pending_resources.html](/C:/MY_PROJECTS/MauryaHub/MauryaHub/templates/admin_pending_resources.html:1)

## Official docs

Render environment variables:

- https://render.com/docs/configure-environment-variables

Google OAuth client for web apps:

- https://docs.cloud.google.com/mcp/set-up-authentication-mcp-servers
- https://docs.cloud.google.com/iam/docs/auth-with-3lo-v2
