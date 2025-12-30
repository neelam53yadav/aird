import { NextRequest, NextResponse } from "next/server"
import { getToken } from "next-auth/jwt"

export async function POST(request: NextRequest) {
  try {
    // Use same secret as NextAuth config (with fallback for consistency)
    const secret = process.env.NEXTAUTH_SECRET || "fallback-secret-for-testing"
    
    // Get NextAuth JWT token (decoded) to access stored backend token
    const decodedToken = await getToken({ 
      req: request, 
      secret: secret,
    })

    if (!decodedToken) {
      return NextResponse.json(
        { error: "No authentication token found" },
        { status: 401 }
      )
    }

    // ALWAYS get a fresh token from backend, don't use cached token
    // This ensures we get a token signed with current keys (important when keys change)
    const cookies = request.cookies
    const nextAuthToken = cookies.get('next-auth.session-token')?.value || 
                         cookies.get('__Secure-next-auth.session-token')?.value ||
                         cookies.get('authjs.session-token')?.value ||
                         cookies.get('__Secure-authjs.session-token')?.value

    if (!nextAuthToken) {
      console.error("NextAuth session token not found in cookies")
      console.log("Available cookies:", Array.from(cookies.getAll()).map(c => c.name))
      return NextResponse.json(
        { error: "NextAuth session token not found" },
        { status: 401 }
      )
    }

    // Always call backend to get a fresh token (signed with current keys)
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"
    const exchangeResponse = await fetch(`${apiUrl}/api/v1/auth/session/exchange`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token: nextAuthToken, // Send NextAuth JWT to backend
      }),
    })

    if (!exchangeResponse.ok) {
      const errorData = await exchangeResponse.json().catch(() => ({ detail: "Exchange failed" }))
      console.error("Backend session exchange failed:", exchangeResponse.status, errorData)
      return NextResponse.json(
        { error: errorData.detail || "Backend token exchange failed" },
        { status: exchangeResponse.status || 500 }
      )
    }

    const exchangeData = await exchangeResponse.json()
    const backendToken = exchangeData.access_token

    if (!backendToken) {
      console.error("No backend access token found after exchange")
      console.log("Decoded token keys:", Object.keys(decodedToken))
      return NextResponse.json(
        { error: "Backend access token not found in session" },
        { status: 401 }
      )
    }

    // Set cookie server-side (backup, but may not be readable by JS)
    const isProduction = process.env.NODE_ENV === "production"
    const nextResponse = NextResponse.json({ 
      ok: true,
      token: backendToken  // Return token so client can set cookie client-side
    })
    
    nextResponse.cookies.set("primedata_api_token", backendToken, {
      httpOnly: false, // Allow JS to read for cross-origin requests
      secure: isProduction,
      sameSite: "lax",
      maxAge: 3600, // 1 hour
      path: "/",
    })

    return nextResponse
  } catch (error) {
    console.error("Token exchange error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
