import { withAuth } from "next-auth/middleware"
import { NextResponse } from "next/server"

export default withAuth(
  function middleware(req) {
    const { pathname } = req.nextUrl
    const token = req.nextauth.token

            // Protected routes
            const protectedRoutes = ["/app", "/account", "/billing", "/dashboard"]
            const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route))

    if (isProtectedRoute && !token) {
      return NextResponse.redirect(new URL("/", req.url))
    }

    return NextResponse.next()
  },
  {
    callbacks: {
              authorized: ({ token, req }) => {
                const { pathname } = req.nextUrl
                const protectedRoutes = ["/app", "/account", "/billing", "/dashboard"]
                const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route))
        
        if (isProtectedRoute) {
          return !!token
        }
        return true
      },
    },
  }
)

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}
