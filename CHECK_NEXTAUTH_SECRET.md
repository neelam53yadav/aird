# How to Check NEXTAUTH_SECRET Match

## 📍 **Where to See Logs**

### **1. Frontend Logs (Next.js)**

#### **Browser Console:**
1. Open your browser
2. Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
3. Go to **Console** tab
4. Look for logs starting with `🔐 TOKEN EXCHANGE DEBUG INFO`

#### **Next.js Server Logs:**
1. Open terminal where Next.js is running
2. Look for console.log output
3. Search for `TOKEN EXCHANGE DEBUG INFO`

**What to look for:**
```
🔐 TOKEN EXCHANGE DEBUG INFO
NEXTAUTH_SECRET (Frontend):
  - Length: 64 characters
  - First 10 chars: abc123xyz...
  - Last 10 chars: ...def456uvw
```

### **2. Backend Logs (FastAPI/Python)**

#### **Terminal/Console:**
1. Open terminal where FastAPI backend is running
2. Look for Python logging output
3. Search for `NEXTAUTH_SECRET` or `KEY DERIVATION INFO`

**What to look for:**
```
Backend NEXTAUTH_SECRET info:
  - Length: 64 characters
  - First 10 chars: abc123xyz...
  - Last 10 chars: ...def456uvw
  - Key derived length: 32 bytes

🔑 KEY DERIVATION INFO
Secret (NEXTAUTH_SECRET):
  - Length: 64 bytes
  - First 10 chars: abc123xyz...
  - Last 10 chars: ...def456uvw
Derived Key (SHA-256 of secret):
  - Length: 32 bytes (32 bytes for AES-256)
  - First 8 bytes (hex): a1b2c3d4e5f6g7h8
```

## 🔍 **How to Compare**

### **Step 1: Check Frontend Secret**

**Location:** Browser console or Next.js server logs

Look for:
```
NEXTAUTH_SECRET (Frontend):
  - Length: <number> characters
  - First 10 chars: <chars>...
  - Last 10 chars: ...<chars>
```

**Note down:**
- Length
- First 10 characters
- Last 10 characters

### **Step 2: Check Backend Secret**

**Location:** Python/FastAPI terminal logs

Look for:
```
Backend NEXTAUTH_SECRET info:
  - Length: <number> characters
  - First 10 chars: <chars>...
  - Last 10 chars: ...<chars>
```

**Note down:**
- Length
- First 10 characters
- Last 10 characters

### **Step 3: Compare**

✅ **They should match:**
- Same length
- Same first 10 characters
- Same last 10 characters

❌ **If they don't match:**
- Update one of the `.env` files to match the other
- Restart both services
- Try again

## 🛠️ **Quick Verification Scripts**

### **Check Frontend Secret**

**File:** `ui/check-secret.js` (create this file)

```javascript
// Run: node check-secret.js
require('dotenv').config({ path: '.env.local' })
const secret = process.env.NEXTAUTH_SECRET

if (!secret) {
  console.log('❌ NEXTAUTH_SECRET not found in .env.local')
} else {
  console.log('✅ Frontend NEXTAUTH_SECRET:')
  console.log(`   Length: ${secret.length} characters`)
  console.log(`   First 10: ${secret.substring(0, 10)}...`)
  console.log(`   Last 10: ...${secret.substring(secret.length - 10)}`)
}
```

### **Check Backend Secret**

**File:** `backend/check_secret.py` (create this file)

```python
# Run: python check_secret.py
import os
from dotenv import load_dotenv

load_dotenv()
secret = os.getenv('NEXTAUTH_SECRET')

if not secret:
    print('❌ NEXTAUTH_SECRET not found in .env')
else:
    print('✅ Backend NEXTAUTH_SECRET:')
    print(f'   Length: {len(secret)} characters')
    print(f'   First 10: {secret[:10]}...')
    print(f'   Last 10: ...{secret[-10:]}')
```

## 📋 **Step-by-Step Debugging**

### **1. Check Frontend .env.local**

**File:** `ui/.env.local`

```bash
# Open file
cat ui/.env.local | grep NEXTAUTH_SECRET

# Or on Windows
type ui\.env.local | findstr NEXTAUTH_SECRET
```

### **2. Check Backend .env**

**File:** `backend/.env`

```bash
# Open file
cat backend/.env | grep NEXTAUTH_SECRET

# Or on Windows
type backend\.env | findstr NEXTAUTH_SECRET
```

### **3. Compare Values**

Copy both values and compare them character by character.

### **4. If They Don't Match**

1. **Choose one secret** (preferably generate a new secure one)
2. **Update both files:**
   - `ui/.env.local`: `NEXTAUTH_SECRET=your-secret`
   - `backend/.env`: `NEXTAUTH_SECRET=your-secret`
3. **Restart both services:**
   - Stop Next.js (Ctrl+C)
   - Stop FastAPI (Ctrl+C)
   - Start Next.js: `npm run dev`
   - Start FastAPI: `uvicorn ...` or your start command
4. **Try again**

## 🎯 **What the Logs Will Show**

### **If Secrets Match:**
```
✅ Token decrypted successfully
✅ JWT verified
✅ User claims extracted
```

### **If Secrets Don't Match:**
```
❌ InvalidTag error
❌ Decryption failed
```

**Check the logs to see:**
- Frontend secret: `abc123xyz...`
- Backend secret: `xyz789abc...` (different!)
- → **They don't match!**

## 📝 **Quick Checklist**

- [ ] Check browser console for frontend secret
- [ ] Check backend terminal for backend secret
- [ ] Compare first 10 characters
- [ ] Compare last 10 characters
- [ ] Compare lengths
- [ ] If different, update one to match the other
- [ ] Restart both services
- [ ] Try token exchange again

## 🔧 **Generate New Secret (If Needed)**

If you need to generate a new secret:

```bash
# Using OpenSSL
openssl rand -base64 32

# Using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"

# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then set the **same value** in both:
- `ui/.env.local`
- `backend/.env`

