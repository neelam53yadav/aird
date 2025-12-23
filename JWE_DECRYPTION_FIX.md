# JWE Decryption Fix

## 🐛 **Error**

```
cryptography.exceptions.InvalidTag
```

This error occurs when the authentication tag doesn't match during AES-GCM decryption, indicating:
1. **Wrong key** - NEXTAUTH_SECRET doesn't match
2. **Wrong data structure** - IV, ciphertext, or tag extracted incorrectly
3. **Wrong key derivation** - Key not derived correctly from secret

## ✅ **Fix Applied**

### **1. Corrected 4-Part JWE Parsing**

**NextAuth 4-part format:**
```
header.empty_key.iv.ciphertext+tag
```

**Parts:**
1. **Header** (base64url): `{"alg":"dir","enc":"A256GCM"}`
2. **Encrypted Key** (empty string for "dir" algorithm)
3. **IV** (base64url): 12-byte initialization vector
4. **Ciphertext+Tag** (base64url): Ciphertext + 16-byte authentication tag (combined)

### **2. Updated Parsing Logic**

**File:** `backend/src/primedata/core/nextauth_verify.py`

```python
# Parse 4-part format
iv_part = token_parts[2]  # IV (base64url)
ciphertext_tag_part = token_parts[3]  # Ciphertext + Tag (combined)

# Decode separately
iv_bytes = base64.urlsafe_b64decode(iv_part)
ciphertext_tag_bytes = base64.urlsafe_b64decode(ciphertext_tag_part)

# Extract tag (last 16 bytes) and ciphertext (rest)
tag_bytes = ciphertext_tag_bytes[-16:]
ciphertext_bytes = ciphertext_tag_bytes[:-16]
```

### **3. Key Derivation**

```python
# Derive 32-byte key using SHA-256 (NextAuth standard)
key = hashlib.sha256(secret.encode('utf-8')).digest()
```

## 🔍 **Verification Steps**

### **Step 1: Verify NEXTAUTH_SECRET Matches**

**Frontend (`ui/.env.local`):**
```env
NEXTAUTH_SECRET=your-secret-here
```

**Backend (`backend/.env`):**
```env
NEXTAUTH_SECRET=your-secret-here
```

**⚠️ CRITICAL:** They must be **identical**!

### **Step 2: Check Frontend Logs**

After the fix, frontend logs will show:
```
Token retrieved from NextAuth:
- Token parts: 4
- Algorithm: dir, Encryption: A256GCM
- NEXTAUTH_SECRET length: 64
- Part 2 (IV) length: <some number>
- Part 3 (ciphertext+tag) length: <some number>
```

### **Step 3: Check Backend Logs**

Backend logs will show:
```
Token type detected - Parts: 4, Algorithm: dir, Encryption: A256GCM
Detected NextAuth compact JWE format (4 parts)
IV length: 12 bytes (expected 12 for GCM)
Ciphertext+Tag length: <some number> bytes
Extracted - IV: 12 bytes, Ciphertext: <X> bytes, Tag: 16 bytes
Key derived from secret (secret length: 64 bytes, key length: 32 bytes)
JWE token decrypted successfully (4-part format)
```

## 🐛 **Common Issues**

### **Issue 1: NEXTAUTH_SECRET Mismatch**

**Symptom:** `InvalidTag` error

**Fix:**
1. Check both `.env` files have the same secret
2. Restart both services after updating
3. Verify secret is not using default/placeholder values

### **Issue 2: Wrong Token Structure**

**Symptom:** Parsing errors or wrong lengths

**Fix:** The code now correctly parses:
- Part 2 = IV (12 bytes after decoding)
- Part 3 = Ciphertext + Tag (combined, tag is last 16 bytes)

### **Issue 3: Key Derivation**

**Symptom:** Decryption fails even with correct secret

**Fix:** The code uses SHA-256 to derive a 32-byte key from the secret, which is the NextAuth standard.

## 📋 **Debugging Checklist**

- [ ] NEXTAUTH_SECRET matches in both `.env` files
- [ ] Secret is not using default/placeholder values
- [ ] Both services restarted after updating secrets
- [ ] Token has 4 parts (check frontend logs)
- [ ] IV is 12 bytes after decoding (check backend logs)
- [ ] Tag is 16 bytes (check backend logs)
- [ ] Key is 32 bytes (check backend logs)

## 🎯 **Next Steps**

1. **Restart backend** to load updated code
2. **Try token exchange** again
3. **Check logs** for:
   - Token structure details
   - IV, ciphertext, tag lengths
   - Key derivation info
   - Any error messages

The updated code should now correctly parse and decrypt NextAuth's 4-part JWE format!

