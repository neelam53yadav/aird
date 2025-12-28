"use client"

import { useState, useEffect } from "react"
import { signIn } from "next-auth/react"
import { useRouter } from "next/navigation"
import { Button } from "./ui/button"
import { exchangeToken } from "@/lib/auth-utils"

interface AuthButtonsProps {
  className?: string
}

export function AuthButtons({ className }: AuthButtonsProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [name, setName] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isSignUp, setIsSignUp] = useState(false)
  const router = useRouter()

  const handleGoogleSignIn = async () => {
    setIsLoading(true)
    try {
      const result = await signIn("google", { 
        callbackUrl: "/dashboard",
        redirect: false 
      })
      
      if (result?.ok) {
        // Exchange token to register user in backend
        const exchangeSuccess = await exchangeToken()
        if (exchangeSuccess) {
          console.log("Token exchange successful")
        } else {
          console.warn("Token exchange failed, but continuing with redirect")
        }
        router.push('/dashboard')
      } else if (result?.error) {
        console.error("Google sign in error:", result.error)
      }
    } catch (error) {
      console.error("Google sign in error:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) return
    if (isSignUp && !name) return

    setIsLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      
      if (isSignUp) {
        // Sign up with email/password
        const response = await fetch(`${apiUrl}/api/v1/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password, name }),
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || "Sign up failed")
        }

        const data = await response.json()
        
        // Sign in with NextAuth using credentials
        const result = await signIn("credentials", {
          email,
          password,
          redirect: false,
        })

        if (result?.ok) {
          const exchangeSuccess = await exchangeToken()
          if (exchangeSuccess) {
            console.log("Token exchange successful")
          }
          router.push('/dashboard')
        } else {
          throw new Error("Failed to sign in after signup")
        }
      } else {
        // Sign in with email/password using NextAuth credentials provider
        const result = await signIn("credentials", {
          email,
          password,
          redirect: false,
        })
        
        if (result?.ok) {
          const exchangeSuccess = await exchangeToken()
          if (exchangeSuccess) {
            console.log("Token exchange successful")
          }
          router.push('/dashboard')
        } else {
          throw new Error(result?.error || "Sign in failed")
        }
      }
    } catch (error) {
      console.error("Email auth error:", error)
      alert(error instanceof Error ? error.message : "Authentication failed")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Google Sign In */}
      <Button
        onClick={handleGoogleSignIn}
        disabled={isLoading}
        className="w-full bg-white text-gray-900 hover:bg-gray-100 border border-gray-300"
        size="lg"
      >
        <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="currentColor"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="currentColor"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          />
          <path
            fill="currentColor"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          />
        </svg>
        {isLoading ? "Signing in..." : "Sign in with Google"}
      </Button>

      {/* Email/Password Auth */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            Or continue with email
          </span>
        </div>
      </div>

      <form onSubmit={handleEmailAuth} className="space-y-4">
        {isSignUp && (
          <input
            type="text"
            placeholder="Full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required={isSignUp}
          />
        )}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
        <Button
          type="submit"
          disabled={isLoading || !email || !password || (isSignUp && !name)}
          variant="outline"
          className="w-full"
          size="lg"
        >
          {isLoading ? (isSignUp ? "Signing up..." : "Signing in...") : (isSignUp ? "Sign up" : "Sign in")}
        </Button>
        <div className="text-center text-sm">
          <button
            type="button"
            onClick={() => setIsSignUp(!isSignUp)}
            className="text-blue-600 hover:text-blue-500"
          >
            {isSignUp ? "Already have an account? Sign in" : "Don't have an account? Sign up"}
          </button>
        </div>
      </form>
    </div>
  )
}
