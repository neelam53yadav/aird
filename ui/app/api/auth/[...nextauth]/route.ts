import NextAuth from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"
import { getApiUrl } from "@/lib/config"

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          throw new Error("Email and password are required")
        }
        
        try {
          // Call your backend login API
          const apiUrl = getApiUrl()
          const res = await fetch(`${apiUrl}/api/v1/auth/login`, {
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
    jwt: async ({ token, user, account }) => {
      if (user) {
        token.iss = "https://nextauth.local"
        token.email = user.email
        token.name = user.name
        token.picture = user.image
        token.provider = account?.provider
        token.roles = ["viewer"] // Default roles
        // Store backend access token for credentials provider
        if ((user as any).access_token) {
          token.backend_access_token = (user as any).access_token
        }
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
