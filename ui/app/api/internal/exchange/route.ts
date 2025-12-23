import { NextRequest, NextResponse } from "next/server"
import { getToken } from "next-auth/jwt"

export async function POST(request: NextRequest) {
  try {
    // Get raw NextAuth JWT
    const token = await getToken({ 
      req: request, 
      secret: process.env.NEXTAUTH_SECRET,
      raw: true 
    })

    if (!token) {
      return NextResponse.json(
        { error: "No authentication token found" },
        { status: 401 }
      )
    }

    // Debug: Log token info (first 100 chars only for security)
    console.log("=".repeat(60))
    console.log("🔐 TOKEN EXCHANGE DEBUG INFO")
    console.log("=".repeat(60))
    console.log("Token retrieved from NextAuth:")
    console.log(`  - Token type: ${typeof token}`)
    console.log(`  - Token length: ${token.length}`)
    console.log(`  - Token parts: ${token.split('.').length}`)
    console.log(`  - Token preview: ${token.substring(0, 100)}...`)
    console.log("")
    console.log("NEXTAUTH_SECRET (Frontend):")
    console.log(`  - Length: ${process.env.NEXTAUTH_SECRET?.length || 'NOT SET'} characters`)
    console.log(`  - First 10 chars: ${process.env.NEXTAUTH_SECRET?.substring(0, 10) || 'NOT SET'}...`)
    console.log(`  - Last 10 chars: ...${process.env.NEXTAUTH_SECRET?.substring(process.env.NEXTAUTH_SECRET.length - 10) || 'NOT SET'}`)
    console.log("=".repeat(60))
    
    // Decode header to check token type
    try {
      const headerPart = token.split('.')[0]
      const headerJson = Buffer.from(headerPart, 'base64url').toString('utf-8')
      const header = JSON.parse(headerJson)
      console.log(`- Token header:`, header)
      console.log(`- Algorithm: ${header.alg}, Encryption: ${header.enc || 'none'}`)
      
      // Log token structure
      const parts = token.split('.')
      console.log(`- Part 0 (header) length: ${parts[0]?.length || 0}`)
      console.log(`- Part 1 (key) length: ${parts[1]?.length || 0} (empty for dir algorithm)`)
      console.log(`- Part 2 (IV) length: ${parts[2]?.length || 0}`)
      console.log(`- Part 3 (ciphertext) length: ${parts[3]?.length || 0}`)
      console.log(`- Part 4 (tag) length: ${parts[4]?.length || 0}`)
      console.log(`- Total parts: ${parts.length} (should be 5 for JWE)`)
    } catch (e) {
      console.warn("Could not decode token header:", e)
    }

    // Exchange token with backend
    const apiBase = "http://127.0.0.1:8000"
    const response = await fetch(`${apiBase}/api/v1/auth/session/exchange`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ token: token }),
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to exchange token" },
        { status: response.status }
      )
    }

    const data = await response.json()

    // Set httpOnly cookie with access token
    const nextResponse = NextResponse.json({ ok: true })
    
    const isProduction = process.env.NODE_ENV === "production"
    nextResponse.cookies.set("primedata_api_token", data.access_token, {
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
