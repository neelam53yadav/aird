# Where to Check Logs for NEXTAUTH_SECRET Match

## 📍 **Quick Answer**

### **Frontend Logs:**
1. **Browser Console** - Press `F12` → Console tab
2. **Next.js Terminal** - Where you ran `npm run dev`

Look for: `🔐 TOKEN EXCHANGE DEBUG INFO`

### **Backend Logs:**
1. **Python/FastAPI Terminal** - Where your backend server is running
2. **Look for:** `Backend NEXTAUTH_SECRET info:` or `🔑 KEY DERIVATION INFO`

---

## 🔍 **Step-by-Step**

### **Step 1: Check Frontend Secret**

#### **Option A: Browser Console**
1. Open your app in browser
2. Press `F12` (or `Ctrl+Shift+I` on Windows, `Cmd+Option+I` on Mac)
3. Click **Console** tab
4. Trigger the token exchange (sign in or visit account page)
5. Look for this section:

```
============================================================
🔐 TOKEN EXCHANGE DEBUG INFO
============================================================
NEXTAUTH_SECRET (Frontend):
  - Length: 64 characters
  - First 10 chars: abc123xyz...
  - Last 10 chars: ...def456uvw
============================================================
```

#### **Option B: Next.js Server Terminal**
1. Find the terminal where you started Next.js (`npm run dev`)
2. Look for the same `🔐 TOKEN EXCHANGE DEBUG INFO` output

---

### **Step 2: Check Backend Secret**

#### **Backend Terminal/Console**
1. Find the terminal where your FastAPI/Python backend is running
2. Look for these log messages:

```
Backend NEXTAUTH_SECRET info:
  - Length: 64 characters
  - First 10 chars: abc123xyz...
  - Last 10 chars: ...def456uvw
  - Key derived length: 32 bytes
```

And later when decrypting:

```
============================================================
🔑 KEY DERIVATION INFO
============================================================
Secret (NEXTAUTH_SECRET):
  - Length: 64 bytes
  - First 10 chars: abc123xyz...
  - Last 10 chars: ...def456uvw
Derived Key (SHA-256 of secret):
  - Length: 32 bytes (32 bytes for AES-256)
  - First 8 bytes (hex): a1b2c3d4e5f6g7h8
============================================================
```

---

## ✅ **How to Compare**

### **Compare These Values:**

1. **Length** - Should be the same number
2. **First 10 chars** - Should be identical
3. **Last 10 chars** - Should be identical

### **Example:**

**Frontend:**
```
Length: 64 characters
First 10 chars: zAFv6-Z8iJ...
Last 10 chars: ...G5Jn6yY
```

**Backend:**
```
Length: 64 characters
First 10 chars: zAFv6-Z8iJ...
Last 10 chars: ...G5Jn6yY
```

✅ **They match!**

---

## 🐛 **If They Don't Match**

### **Fix Steps:**

1. **Check `.env` files directly:**

   **Frontend:** `ui/.env.local`
   ```env
   NEXTAUTH_SECRET=your-secret-here
   ```

   **Backend:** `backend/.env`
   ```env
   NEXTAUTH_SECRET=your-secret-here
   ```

2. **Make them identical:**
   - Copy the secret from one file
   - Paste it into the other file
   - Save both files

3. **Restart both services:**
   - Stop Next.js (Ctrl+C in Next.js terminal)
   - Stop Backend (Ctrl+C in backend terminal)
   - Start Next.js: `cd ui && npm run dev`
   - Start Backend: `cd backend && uvicorn ...` (or your start command)

4. **Try again:**
   - Sign in again
   - Check logs again
   - Verify secrets match

---

## 📋 **Quick Commands to Check Secrets**

### **Windows (PowerShell):**

**Check Frontend:**
```powershell
cd ui
Get-Content .env.local | Select-String "NEXTAUTH_SECRET"
```

**Check Backend:**
```powershell
cd backend
Get-Content .env | Select-String "NEXTAUTH_SECRET"
```

### **Linux/Mac:**

**Check Frontend:**
```bash
cd ui
grep NEXTAUTH_SECRET .env.local
```

**Check Backend:**
```bash
cd backend
grep NEXTAUTH_SECRET .env
```

---

## 🎯 **What to Look For in Logs**

### **When Token Exchange Happens:**

**Frontend logs will show:**
```
🔐 TOKEN EXCHANGE DEBUG INFO
NEXTAUTH_SECRET (Frontend):
  - Length: 64 characters
  - First 10 chars: <check this>
  - Last 10 chars: <check this>
```

**Backend logs will show:**
```
Backend NEXTAUTH_SECRET info:
  - Length: 64 characters
  - First 10 chars: <check this>
  - Last 10 chars: <check this>

🔑 KEY DERIVATION INFO
Secret (NEXTAUTH_SECRET):
  - First 10 chars: <check this>
  - Last 10 chars: <check this>
```

**Compare the "First 10 chars" and "Last 10 chars" - they must be identical!**

---

## ⚠️ **Common Issues**

### **Issue 1: Can't Find Logs**

**Frontend:**
- Make sure browser console is open (F12)
- Make sure you're on the Console tab (not Network or Elements)
- Try signing in again to trigger the exchange

**Backend:**
- Make sure backend server is running
- Check the terminal where you started the server
- Look for Python logging output

### **Issue 2: Logs Don't Show Secret Info**

**Solution:**
- Restart both services (the new logging code needs to be loaded)
- Make sure you're using the latest code
- Try the token exchange again

### **Issue 3: Secrets Look Different in Logs**

**Solution:**
- They MUST be identical
- Copy one secret exactly (including all characters)
- Paste into the other `.env` file
- Restart both services
- Check logs again

---

## 🎯 **Summary**

1. **Frontend logs:** Browser console (F12) or Next.js terminal
2. **Backend logs:** Python/FastAPI terminal
3. **Compare:** First 10 chars and Last 10 chars must match
4. **If different:** Update one `.env` file to match the other
5. **Restart:** Both services after updating

The logs will now clearly show the secret values (first/last 10 chars) so you can easily compare them!

