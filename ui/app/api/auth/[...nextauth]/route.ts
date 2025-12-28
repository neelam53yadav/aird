import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import CredentialsProvider from "next-auth/providers/credentials"

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
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null
        }
        
        // Call your backend login API
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        const res = await fetch(`${apiUrl}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: credentials.email,
            password: credentials.password,
          }),
        })
        
        if (!res.ok) {
          return null
        }
        
        const data = await res.json()
        
        // Return user object that NextAuth expects
        return {
          id: data.user.id,
          email: data.user.email,
          name: data.user.name,
          image: data.user.picture_url,
          access_token: data.access_token, // Store backend token for session exchange
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
        token.google_sub = account?.provider === "google" ? account.providerAccountId : null
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
        (session.user as any).google_sub = token.google_sub as string | null
      }
      return session
    },
    redirect: async ({ url, baseUrl }) => {
      console.log("Redirect callback called:", { url, baseUrl })
      
      // Always redirect to dashboard after successful login
      if (url === baseUrl || url === `${baseUrl}/`) {
        console.log("Redirecting from base URL to dashboard")
        return `${baseUrl}/dashboard`
      }
      
      // If it's a relative URL, make it absolute
      if (url.startsWith("/")) {
        const redirectUrl = `${baseUrl}${url}`
        console.log("Redirecting to:", redirectUrl)
        return redirectUrl
      }
      
      // If it's the same origin, allow it
      if (url.startsWith(baseUrl)) {
        console.log("Same origin, allowing:", url)
        return url
      }
      
      // Default redirect to dashboard
      const defaultRedirect = `${baseUrl}/dashboard`
      console.log("Default redirect to:", defaultRedirect)
      return defaultRedirect
    },
  },
  pages: {
    signIn: '/', // Use the landing page as sign-in page
    error: '/', // Redirect errors to landing page
  },
  secret: process.env.NEXTAUTH_SECRET || "fallback-secret-for-testing",
})

export { handler as GET, handler as POST }
