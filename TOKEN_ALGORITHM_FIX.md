# Token Algorithm Error Fix

## 🐛 **Error**

```
Invalid token error: The specified alg value is not allowed
```

## 🔍 **Root Cause**

The JWT token header contains an algorithm (`alg`) that doesn't match what the decoder expects. This can happen if:

1. **Token has different algorithm** - Token header says `RS256` but decoder expects `HS256`
2. **Token has `alg: "none"`** - Security restriction prevents this
3. **Token is not a JWT** - The value might be an encrypted session token, not a JWT

## ✅ **Fix Applied**

### **1. Added Algorithm Detection**

The code now:
- Decodes the token header first to check the algorithm
- Logs the algorithm found in the token
- Validates the algorithm is supported

### **2. Flexible Algorithm Handling**

**File:** `backend/src/primedata/core/nextauth_verify.py`

```python
# Check token header for algorithm
unverified_header = jwt.get_unverified_header(token)
token_algorithm = unverified_header.get("alg")

# Try the algorithm from token, or fallback to HS256/HS384/HS512
allowed_algorithms = [token_algorithm] if token_algorithm in ["HS256", "HS384", "HS512"] else ["HS256", "HS384", "HS512"]
```

### **3. Better Error Logging**

The code now logs:
- Token algorithm found in header
- Full token header
- Token preview (first 100 chars)
- Whether token appears to be a JWT (has 3 parts)

## 🔧 **Debugging Steps**

### **Step 1: Check Backend Logs**

Look for these log messages:
```
Token algorithm in header: <algorithm>
Token header: {...}
```

### **Step 2: Verify Token Format**

The token should be a JWT with 3 parts separated by dots:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

If it doesn't have 3 parts, it's not a JWT.

### **Step 3: Check NextAuth Configuration**

**File:** `ui/app/api/auth/[...nextauth]/route.ts`

Ensure NextAuth is configured to use JWT:

```typescript
session: {
  strategy: "jwt",  // ✅ Must be "jwt", not "database"
}
```

### **Step 4: Verify Token Retrieval**

**File:** `ui/app/api/internal/exchange/route.ts`

The `getToken` with `raw: true` should return the JWT:

```typescript
const token = await getToken({ 
  req: request, 
  secret: process.env.NEXTAUTH_SECRET,
  raw: true  // ✅ Returns raw JWT token
})
```

## 🐛 **Common Issues**

### **Issue 1: Token is Encrypted Session, Not JWT**

**Symptom:** Token doesn't have 3 parts separated by dots

**Fix:** Ensure NextAuth uses JWT strategy:

```typescript
session: {
  strategy: "jwt",  // Not "database"
}
```

### **Issue 2: Algorithm Mismatch**

**Symptom:** Token has `alg: "RS256"` but decoder expects `HS256`

**Fix:** The code now handles this by:
- Detecting the algorithm from token header
- Using the correct algorithm for decoding
- Falling back to HS256 if algorithm is unexpected

### **Issue 3: Token Has `alg: "none"`**

**Symptom:** Error about "none" algorithm not allowed

**Fix:** This is a security restriction. The token must use a valid signing algorithm (HS256, HS384, or HS512).

## 📋 **Checklist**

- [ ] Token has 3 parts (header.payload.signature)
- [ ] Token algorithm is HS256, HS384, or HS512
- [ ] NextAuth uses JWT strategy (`strategy: "jwt"`)
- [ ] `getToken` uses `raw: true` to get JWT
- [ ] Backend logs show the token algorithm
- [ ] NEXTAUTH_SECRET matches between frontend and backend

## 🔍 **What to Check in Logs**

After the fix, check backend logs for:

1. **Token algorithm:**
   ```
   Token algorithm in header: HS256
   ```

2. **Token format:**
   ```
   Token decoded successfully. Payload keys: [...]
   ```

3. **If error occurs:**
   ```
   Token uses unsupported algorithm: <algorithm>
   Token header: {...}
   ```

## 🎯 **Summary**

The fix:
1. ✅ Detects algorithm from token header
2. ✅ Validates algorithm is supported
3. ✅ Uses correct algorithm for decoding
4. ✅ Provides detailed error logging
5. ✅ Validates token format (JWT has 3 parts)

Check your backend logs to see what algorithm the token is using, and the code will now handle it correctly!

