# AdaptiFocus — Local Testing & Chrome Web Store Publishing Guide

## 🧪 Step 1: Test Locally (Do This First!)

### Start the backend
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

### Load extension in Chrome
1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode** (toggle top-right)
3. Click **"Load unpacked"** → Select the `extension/` folder
4. Click the AdaptiFocus icon in the toolbar
5. Click **"🔧 Dev Login (Local Testing)"** → You're logged in!

### Test classification
- Visit `youtube.com` → Should show "distraction"
- Visit YouTube and search "MIT algorithm lecture" → Should show "study" ✅
- Visit `scholar.google.com` → Should show "study"
- Visit `instagram.com` → Should show "distraction"

### Start the dashboard (optional)
```bash
cd dashboard
npm run dev
```

---

## 🏪 Step 2: Publish to Chrome Web Store

### 2a. Upload as Draft
1. Go to [Chrome Developer Dashboard](https://chrome.google.com/webstore/devconsole)
2. Click **"New Item"**
3. Upload `extension.zip` (at project root)
4. Fill in store listing (copy from `extension/store_listing.md`)
5. **Don't publish yet** — just save as draft
6. Copy the **Extension ID** from the dashboard URL

### 2b. Create Google OAuth Client
1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **"Create Project"** → Name: "AdaptiFocus"
3. Click **"Create Credentials"** → **OAuth Client ID**
4. Application type: **Chrome Extension**
5. Item ID: Paste the Extension ID from step 2a
6. Copy the **Client ID** (looks like `xxx.apps.googleusercontent.com`)

### 2c. Update & Republish
1. In `extension/manifest.json`, replace `YOUR_GOOGLE_CLIENT_ID` with your Client ID
2. In `popup/popup.js`, change `API_BASE` to your deployed server URL
3. Re-zip: `cd extension && zip -r ../extension.zip . -x ".*" "store_listing.md"`
4. Re-upload to Chrome Web Store
5. Click **"Submit for Review"** (takes 1-3 business days)

---

## 🚀 Step 3: Deploy Backend

### Option A: Railway (Easiest)
1. Go to [railway.app](https://railway.app) → New Project
2. Add **PostgreSQL** service → Copy `DATABASE_URL`
3. Add **Python** service → Connect your GitHub repo
4. Set environment variables:
   - `DATABASE_URL` = (from PostgreSQL service)
   - `JWT_SECRET` = (generate: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `GOOGLE_CLIENT_ID` = (from step 2b)
   - `DEV_MODE` = `0` (disables dev login in production)

### Option B: Render
1. Go to [render.com](https://render.com) → New Web Service
2. Connect your repo → Set build command: `pip install -r requirements.txt`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add PostgreSQL database
5. Set same env vars as above

---

## ✅ Verification Checklist
- [ ] Backend starts locally with `uvicorn main:app --reload`
- [ ] Extension loads in Chrome (unpacked)
- [ ] Dev Login works in popup
- [ ] YouTube cat videos → "distraction"
- [ ] YouTube lectures → "study" or "neutral"
- [ ] Extension uploaded to Chrome Web Store as draft
- [ ] Google OAuth Client ID created
- [ ] Backend deployed to Railway/Render
- [ ] Extension published with production URLs
