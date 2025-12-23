# Authentication Flow Analysis

## 🔍 **Current Authentication Flow**

### **1. User Clicks "Sign In"**

**Location:** `ui/app/page.tsx:27-45` or `ui/components/AuthButtons.tsx:24-42`

```typescript
const handleGoogleSignIn = async () => {
  const result = await signIn("google", { 
    callbackUrl: "/dashboard",
    redirect: false
  })
  if (result?.ok) {
    router.push('/dashboard')
  }
}
```

**What Happens:**
- ✅ NextAuth handles Google OAuth
- ✅ User authenticates with Google
- ✅ NextAuth creates a session token (JWT)
- ✅ User is redirected to `/dashboard`

**❌ PROBLEM:** The `/api/v1/auth/session/exchange` endpoint is **NOT called** at this point!

---

### **2. When is `/api/v1/auth/session/exchange` Called?**

**Currently, it's ONLY called on the Account page:**

**Location:** `ui/app/account/page.tsx:27-32`

```typescript
useEffect(() => {
  if (status === "authenticated") {
    // Exchange NextAuth token for backend token
    fetch("/api/internal/exchange", {
      method: "POST",
    })
    // ...
  }
}, [status])
```

**This means:**
- ❌ User signs in → No backend registration yet
- ❌ User goes to dashboard → Still no backend registration
- ✅ User visits `/account` page → **NOW** the exchange happens and user is registered

---

### **3. The Exchange Flow (When It Happens)**

#### **Step 1: Frontend calls `/api/internal/exchange`**

**Location:** `ui/app/api/internal/exchange/route.ts:4-59`

```typescript
export async function POST(request: NextRequest) {
  // Get raw NextAuth JWT
  const token = await getToken({ 
    req: request, 
    secret: process.env.NEXTAUTH_SECRET,
    raw: true 
  })

  // Exchange token with backend
  const response = await fetch(`${apiBase}/api/v1/auth/session/exchange`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ nextauth_token: token }),  // ⚠️ BUG: Wrong parameter name!
  })
}
```

**⚠️ BUG FOUND:** Frontend sends `nextauth_token` but backend expects `token`!

#### **Step 2: Backend receives request**

**Location:** `backend/src/primedata/api/auth.py:53-160`

```python
@router.post("/api/v1/auth/session/exchange", response_model=SessionExchangeResponse)
async def exchange_session(
    request: SessionExchangeRequest,  # Expects: { "token": "..." }
    db: Session = Depends(get_db)
):
    # Verify NextAuth token
    claims = verify_nextauth_token(request.token)  # ⚠️ Will fail because request.token is None!
```

**Expected Request Model:**
```python
class SessionExchangeRequest(BaseModel):
    token: str  # ⚠️ Expects "token", not "nextauth_token"
```

**⚠️ BUG:** Parameter mismatch will cause the exchange to fail!

---

### **4. User Registration in Backend**

**Location:** `backend/src/primedata/api/auth.py:83-106`

```python
# Upsert user
user = db.query(User).filter(User.email == email).first()

if not user:
    # Create new user ✅ THIS IS WHERE USER IS REGISTERED
    user = User(
        email=email,
        name=name,
        picture_url=picture,
        auth_provider=AuthProvider(provider) if provider else AuthProvider.NONE,
        google_sub=google_sub,
        roles=["viewer"]
    )
    db.add(user)
    db.commit()
    db.refresh(user)
else:
    # Update existing user
    user.name = name
    user.picture_url = picture
    # ...
    db.commit()
```

**This happens:**
- ✅ When `/api/v1/auth/session/exchange` is successfully called
- ✅ User is created in the `users` table
- ✅ Default workspace is created if user has no workspaces
- ✅ User is added to workspace as OWNER

---

## 🐛 **Issues Found**

### **Issue 1: Parameter Mismatch**

**Frontend sends:**
```json
{ "nextauth_token": "..." }
```

**Backend expects:**
```json
{ "token": "..." }
```

**Fix needed in:** `ui/app/api/internal/exchange/route.ts:27`

---

### **Issue 2: Exchange Not Called on Sign-In**

**Current behavior:**
- User signs in → NextAuth session created
- User redirected to dashboard → **No backend registration**
- User must visit `/account` page → **Then** exchange happens

**Expected behavior:**
- User signs in → NextAuth session created
- **Immediately call exchange** → Backend registration happens
- User redirected to dashboard → Already registered

**Fix needed:** Call exchange immediately after sign-in, not just on account page.

---

### **Issue 3: Exchange Only on Account Page**

**Current:** Exchange is only triggered when user visits `/account` page.

**Problem:** 
- If user never visits `/account`, they're never registered in backend
- Dashboard and other pages won't work properly without backend token

**Fix needed:** Call exchange on:
- ✅ After successful sign-in (before redirect)
- ✅ On dashboard page load (if not already exchanged)
- ✅ On any protected page (as fallback)

---

## ✅ **How User Registration Works (When Fixed)**

1. **User clicks "Sign in with Google"**
   - NextAuth handles OAuth
   - NextAuth session created

2. **After successful sign-in:**
   - Frontend calls `/api/internal/exchange`
   - This calls `/api/v1/auth/session/exchange` with NextAuth token

3. **Backend `/api/v1/auth/session/exchange`:**
   - Verifies NextAuth token
   - Extracts user info (email, name, picture, provider)
   - **Creates user in database** (if doesn't exist)
   - **Updates user** (if exists)
   - Creates default workspace (if user has none)
   - Returns backend JWT token

4. **Frontend stores backend token:**
   - Sets `primedata_api_token` cookie (httpOnly)
   - User can now make authenticated API calls

5. **User redirected to dashboard:**
   - Already registered in backend
   - Backend token available for API calls

---

## 🔧 **Recommended Fixes**

### **Fix 1: Correct Parameter Name**

**File:** `ui/app/api/internal/exchange/route.ts:27`

**Change:**
```typescript
body: JSON.stringify({ nextauth_token: token }),
```

**To:**
```typescript
body: JSON.stringify({ token: token }),
```

---

### **Fix 2: Call Exchange After Sign-In**

**Option A: In sign-in handler**

**File:** `ui/app/page.tsx` or `ui/components/AuthButtons.tsx`

```typescript
const handleGoogleSignIn = async () => {
  const result = await signIn("google", { 
    callbackUrl: "/dashboard",
    redirect: false
  })
  
  if (result?.ok) {
    // Exchange token immediately after sign-in
    await fetch("/api/internal/exchange", { method: "POST" })
    router.push('/dashboard')
  }
}
```

**Option B: In middleware or layout**

Create a middleware that calls exchange on authenticated pages.

---

### **Fix 3: Call Exchange on Dashboard**

**File:** `ui/app/dashboard/page.tsx` (or create if doesn't exist)

```typescript
useEffect(() => {
  if (status === "authenticated") {
    // Exchange token if not already done
    fetch("/api/internal/exchange", { method: "POST" })
  }
}, [status])
```

---

## 📊 **Summary**

| Step | Current Behavior | Expected Behavior |
|------|-----------------|-------------------|
| User clicks sign-in | ✅ NextAuth handles auth | ✅ NextAuth handles auth |
| After sign-in | ❌ No backend call | ✅ Call exchange immediately |
| User redirected | ✅ To dashboard | ✅ To dashboard |
| Backend registration | ❌ Only on `/account` page | ✅ Immediately after sign-in |
| Parameter name | ❌ `nextauth_token` | ✅ `token` |

**The `/api/v1/auth/session/exchange` endpoint IS being called, but:**
1. ⚠️ Only on the account page (not after sign-in)
2. ⚠️ With wrong parameter name (`nextauth_token` instead of `token`)
3. ⚠️ User registration happens, but too late

**User IS registered in the backend, but only when they visit `/account` page, not immediately after sign-in.**

