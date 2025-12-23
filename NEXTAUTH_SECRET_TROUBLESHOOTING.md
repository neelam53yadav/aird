# NextAuth Secret Troubleshooting Guide

## 🐛 **Problem**

Token verification fails with `401 Unauthorized` when calling `/api/v1/auth/session/exchange`.

## 🔍 **Root Cause**

The `NEXTAUTH_SECRET` environment variable **MUST be identical** in both:
- **Frontend** (`ui/.env.local`)
- **Backend** (`backend/.env`)

If they don't match, the token cannot be decoded because:
- Frontend signs the token with its `NEXTAUTH_SECRET`
- Backend tries to verify with its `NEXTAUTH_SECRET`
- If secrets differ → Signature verification fails → Token rejected

## ✅ **Solution**

### **Step 1: Generate a Secure Secret**

Generate a random 32+ character secret:

```bash
# Using OpenSSL
openssl rand -base64 32

# Or using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"

# Or using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### **Step 2: Set in Frontend**

**File:** `ui/.env.local`

```env
NEXTAUTH_SECRET=your-generated-secret-here
NEXTAUTH_URL=http://localhost:3000
```

### **Step 3: Set in Backend**

**File:** `backend/.env`

```env
NEXTAUTH_SECRET=your-generated-secret-here
API_SESSION_EXCHANGE_ALLOWED_ISS=https://nextauth.local
```

**⚠️ CRITICAL:** The secret must be **EXACTLY THE SAME** in both files!

### **Step 4: Restart Services**

After updating environment variables:

1. **Restart Frontend:**
   ```bash
   cd ui
   npm run dev
   ```

2. **Restart Backend:**
   ```bash
   cd backend
   # Stop and restart your FastAPI server
   ```

## 🔍 **Verification**

### **Check Frontend Secret**

```bash
cd ui
node -e "console.log('Frontend NEXTAUTH_SECRET:', process.env.NEXTAUTH_SECRET || 'NOT SET')"
```

### **Check Backend Secret**

```bash
cd backend
python -c "from primedata.core.settings import get_settings; print('Backend NEXTAUTH_SECRET:', get_settings().NEXTAUTH_SECRET)"
```

### **Compare Secrets**

They should be **identical**. If different, token verification will fail.

## 🐛 **Common Issues**

### **Issue 1: Default Values Don't Match**

**Frontend default:** `"fallback-secret-for-testing"`  
**Backend default:** `"REPLACE_WITH_64_CHAR_RANDOM_STRING_FOR_PRODUCTION_USE_ONLY"`

**Fix:** Set the same secret in both `.env` files.

### **Issue 2: Secret Not Loaded**

**Symptoms:**
- Backend logs show: `"NEXTAUTH_SECRET is not set or using default value"`
- Token verification fails

**Fix:**
1. Check `.env` file exists in `backend/` directory
2. Check `.env.local` file exists in `ui/` directory
3. Verify variable name is exactly `NEXTAUTH_SECRET` (case-sensitive)
4. Restart services after adding/updating `.env` files

### **Issue 3: Issuer Mismatch**

**Backend expects:** `https://nextauth.local`  
**Token has:** Different issuer

**Fix:** Ensure NextAuth callback sets the issuer:

**File:** `ui/app/api/auth/[...nextauth]/route.ts`

```typescript
jwt: async ({ token, user, account }) => {
  if (user) {
    token.iss = "https://nextauth.local"  // ✅ Must match backend setting
    // ...
  }
  return token
}
```

**Backend setting:** `API_SESSION_EXCHANGE_ALLOWED_ISS=https://nextauth.local`

### **Issue 4: Token Format Issues**

**Symptoms:**
- `DecodeError` in logs
- Token appears malformed

**Fix:**
- Ensure frontend is sending the raw token (not encoded/escaped)
- Check `ui/app/api/internal/exchange/route.ts` uses `raw: true`:

```typescript
const token = await getToken({ 
  req: request, 
  secret: process.env.NEXTAUTH_SECRET,
  raw: true  // ✅ Must be true
})
```

## 📋 **Checklist**

- [ ] `NEXTAUTH_SECRET` set in `ui/.env.local`
- [ ] `NEXTAUTH_SECRET` set in `backend/.env`
- [ ] Both secrets are **identical**
- [ ] Secrets are not using default/placeholder values
- [ ] Frontend service restarted after updating `.env.local`
- [ ] Backend service restarted after updating `.env`
- [ ] `API_SESSION_EXCHANGE_ALLOWED_ISS` matches token issuer
- [ ] Token is being sent as raw JWT (not encoded)

## 🔧 **Debug Steps**

### **1. Check Token Reception**

**Backend:** `backend/src/primedata/api/auth.py:69`

```python
print("xcahne session")
print(request.token)  # Should print the JWT token
```

### **2. Check Secret Values**

**Backend:** Add temporary logging:

```python
from primedata.core.settings import get_settings
settings = get_settings()
print(f"Backend NEXTAUTH_SECRET length: {len(settings.NEXTAUTH_SECRET)}")
print(f"Backend NEXTAUTH_SECRET first 10 chars: {settings.NEXTAUTH_SECRET[:10]}")
```

**Frontend:** Check in `ui/app/api/internal/exchange/route.ts`:

```typescript
console.log("Frontend NEXTAUTH_SECRET length:", process.env.NEXTAUTH_SECRET?.length)
console.log("Frontend NEXTAUTH_SECRET first 10 chars:", process.env.NEXTAUTH_SECRET?.substring(0, 10))
```

### **3. Check Token Decode**

**Backend:** Improved error logging in `nextauth_verify.py` will show:
- Invalid signature errors
- Decode errors
- Expiration errors
- Issuer mismatches

## 📝 **Example .env Files**

### **Frontend (`ui/.env.local`)**

```env
NEXTAUTH_SECRET=zAFv6-Z8iJJ1wla4U0-tS8UsV_v2f5u0QvTNXJwJIJZhR6yRpAH0DRGBiG5Jn6yY
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### **Backend (`backend/.env`)**

```env
NEXTAUTH_SECRET=zAFv6-Z8iJJ1wla4U0-tS8UsV_v2f5u0QvTNXJwJIJZhR6yRpAH0DRGBiG5Jn6yY
API_SESSION_EXCHANGE_ALLOWED_ISS=https://nextauth.local
DATABASE_URL=postgresql+psycopg2://primedata:primedata123@localhost:5433/primedata
```

**⚠️ Notice:** `NEXTAUTH_SECRET` is **identical** in both files!

## 🎯 **Summary**

The token verification fails because:

1. **Frontend** signs token with `NEXTAUTH_SECRET` from `ui/.env.local`
2. **Backend** verifies token with `NEXTAUTH_SECRET` from `backend/.env`
3. **If secrets don't match** → Signature verification fails → 401 Unauthorized

**Fix:** Ensure both `.env` files have the **exact same** `NEXTAUTH_SECRET` value.

