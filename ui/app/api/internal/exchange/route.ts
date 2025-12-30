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

    // For simple authentication (credentials provider), backend token is stored in NextAuth session
    const backendToken = (decodedToken as any).backend_access_token

    if (!backendToken) {
      console.error("No backend access token found in NextAuth session")
      console.log("Decoded token keys:", Object.keys(decodedToken))
      return NextResponse.json(
        { error: "Backend access token not found in session" },
        { status: 401 }
      )
    }

    // Set httpOnly cookie with backend access token
    const nextResponse = NextResponse.json({ ok: true })
    const isProduction = process.env.NODE_ENV === "production"
    nextResponse.cookies.set("primedata_api_token", backendToken, {
      httpOnly: true,
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
