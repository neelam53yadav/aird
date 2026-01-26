import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import CredentialsProvider from "next-auth/providers/credentials"
import { getApiUrl } from "@/lib/config"

// Helper function to decode JWT token without verification (for extracting workspace_ids)
function decodeJWT(token: string): any {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    
    // Decode base64url payload (second part)
    const payload = parts[1]
    // Replace URL-safe base64 characters
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    // Add padding if needed
    const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
    const decoded = Buffer.from(padded, 'base64').toString('utf-8')
    return JSON.parse(decoded)
  } catch (error) {
    console.error('Failed to decode JWT:', error)
    return null
  }
}

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "dummy",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "dummy",
    }),
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
        invitation_token: { label: "Invitation Token", type: "text" }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          throw new Error("Email and password are required")
        }
        
        try {
          // Call your backend login API
          const apiUrl = getApiUrl()
          let loginUrl = `${apiUrl}/api/v1/auth/login`
          
          // Add invitation_token as query parameter if provided
          if (credentials.invitation_token) {
            console.log('[NextAuth] Passing invitation_token to backend:', credentials.invitation_token.substring(0, 20) + '...')
            loginUrl += `?invitation_token=${encodeURIComponent(credentials.invitation_token)}`
          } else {
            console.log('[NextAuth] No invitation_token provided in credentials')
          }
          
          const res = await fetch(loginUrl, {
            method: "POST",
            headers: { 
              "Content-Type": "application/json",
              // Explicitly don't include any auth headers or cookies
            },
            // Explicitly exclude cookies and credentials
            credentials: "omit",
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          })
          
          if (!res.ok) {
            // Try to get error message from backend
            let errorMessage = "Invalid email or password"
            try {
              const errorData = await res.json()
              if (errorData.detail) {
                errorMessage = errorData.detail
              }
            } catch {
              // If parsing fails, use default message
            }
            throw new Error(errorMessage)
          }
          
          const data = await res.json()
          
          // Validate response structure
          if (!data.user || !data.access_token) {
            throw new Error("Invalid response from server")
          }
          
          // Return user object that NextAuth expects
          return {
            id: data.user.id,
            email: data.user.email,
            name: data.user.name,
            image: data.user.picture_url,
            access_token: data.access_token, // Store backend token for session exchange
          }
        } catch (error) {
          // Re-throw the error so NextAuth can pass it to the client
          if (error instanceof Error) {
            throw error
          }
          throw new Error("Authentication failed")
        }
      }
    })
  ],
  session: {
    strategy: "jwt",
  },
  callbacks: {
    jwt: async ({ token, user, account, trigger }) => {
      if (user) {
        token.iss = "https://nextauth.local"
        token.email = user.email
        token.name = user.name
        token.picture = user.image
        token.provider = account?.provider
        token.google_sub = account?.provider === "google" ? account.providerAccountId : null
        token.roles = ["viewer"] // Default roles
        // Store backend access token for credentials provider
        if ((user as any).access_token) {
          token.backend_access_token = (user as any).access_token
          
          // Decode backend JWT to extract workspace_ids
          const decoded = decodeJWT((user as any).access_token)
          if (decoded && decoded.workspaces) {
            token.workspace_ids = decoded.workspaces
          }
        }
      }
      
      // If this is a session update (e.g., after token exchange), refresh workspace_ids
      if (trigger === "update") {
        // Try to get the latest backend token from the request
        // The exchange endpoint sets primedata_api_token cookie with fresh token
        // We'll decode the stored backend_access_token first, then try to get a fresh one
        if (token.backend_access_token) {
          const decoded = decodeJWT(token.backend_access_token as string)
          if (decoded && decoded.workspaces) {
            token.workspace_ids = decoded.workspaces
          }
        }
        // Note: The exchange endpoint gets a fresh token with updated workspace_ids
        // The token is stored in primedata_api_token cookie, but we can't access it here
        // The workspace_ids should be updated when the token is initially set during login
      }
      
      return token
    },
    session: async ({ session, token }) => {
      if (token) {
        // Update session user with token data
        if (session.user) {
          session.user.email = token.email as string
          session.user.name = token.name as string
          session.user.image = token.picture as string
        }
        // Add custom properties to session
        (session as any).iss = token.iss as string
        (session.user as any).roles = token.roles as string[]
        (session.user as any).google_sub = token.google_sub as string | null
        (session.user as any).workspace_ids = (token.workspace_ids as string[]) || []
      }
      return session
    },
    redirect: async ({ url, baseUrl }) => {
      // Always redirect to dashboard after successful login
      if (url === baseUrl || url === `${baseUrl}/`) {
        return `${baseUrl}/dashboard`
      }
      
      // If it's a relative URL, make it absolute
      if (url.startsWith("/")) {
        return `${baseUrl}${url}`
      }
      
      // If it's the same origin, allow it
      if (url.startsWith(baseUrl)) {
        return url
      }
      
      // Default redirect to dashboard
      return `${baseUrl}/dashboard`
    },
  },
  pages: {
    signIn: '/', // Use the landing page as sign-in page
    error: '/', // Redirect errors to landing page
  },
  secret: process.env.NEXTAUTH_SECRET || "fallback-secret-for-testing",
})

export { handler as GET, handler as POST }
