import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "dummy",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "dummy",
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
