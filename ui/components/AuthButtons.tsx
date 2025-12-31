"use client"

import { useState } from "react"
import { signIn } from "next-auth/react"
import { useRouter } from "next/navigation"
import { Button } from "./ui/button"
import { exchangeToken } from "@/lib/auth-utils"
import { Mail, Lock, User, CheckCircle2, X } from "lucide-react"

interface AuthButtonsProps {
  className?: string
}

// Password complexity requirements
interface PasswordRequirements {
  minLength: boolean
  hasUpperCase: boolean
  hasLowerCase: boolean
  hasNumber: boolean
  hasSpecialChar: boolean
}

export function AuthButtons({ className }: AuthButtonsProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [name, setName] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isSignUp, setIsSignUp] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  // Check password complexity
  const checkPasswordRequirements = (pwd: string): PasswordRequirements => {
    return {
      minLength: pwd.length >= 8,
      hasUpperCase: /[A-Z]/.test(pwd),
      hasLowerCase: /[a-z]/.test(pwd),
      hasNumber: /[0-9]/.test(pwd),
      hasSpecialChar: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pwd),
    }
  }

  const passwordRequirements = checkPasswordRequirements(password)
  const isPasswordValid = Object.values(passwordRequirements).every(Boolean)
  const passwordsMatch = !isSignUp || password === confirmPassword

  const handleGoogleSignIn = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await signIn("google", {
        callbackUrl: "/dashboard",
        redirect: false,
      })

      if (result?.ok) {
        // Exchange token to register user in backend
        const exchangeResult = await exchangeToken()
        if (exchangeResult.success) {
          console.log("Token exchange successful")
        } else {
          console.warn("Token exchange failed, but continuing with redirect")
        }
        router.push("/dashboard")
      } else if (result?.error) {
        setError(result.error || "Google sign in failed")
      }
    } catch (error) {
      console.error("Google sign in error:", error)
      setError("An unexpected error occurred")
    } finally {
      setIsLoading(false)
    }
  }

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    
    if (!email || !password) {
      setError("Please fill in all fields")
      return
    }
    
    if (isSignUp) {
      if (!name) {
        setError("Please enter your name")
        return
      }
      
      if (!isPasswordValid) {
        setError("Password does not meet complexity requirements")
        return
      }
      
      if (password !== confirmPassword) {
        setError("Passwords do not match")
        return
      }
    }

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
          const exchangeResult = await exchangeToken()
          if (exchangeResult.success) {
            console.log("Token exchange successful")
            await new Promise((resolve) => setTimeout(resolve, 100))
          } else {
            console.warn("Token exchange failed, but continuing with redirect")
          }
          router.push("/dashboard")
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
          const exchangeResult = await exchangeToken()
          if (exchangeResult.success) {
            console.log("Token exchange successful")
            await new Promise((resolve) => setTimeout(resolve, 100))
          } else {
            console.warn("Token exchange failed, but continuing with redirect")
          }
          router.push("/dashboard")
        } else {
          throw new Error(result?.error || "Sign in failed")
        }
      }
    } catch (error) {
      console.error("Email auth error:", error)
      setError(error instanceof Error ? error.message : "Authentication failed")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Dynamic Header Text */}
      <div className="text-center mb-4">
        <p className="text-base md:text-lg text-gray-600">
          {isSignUp ? "Create your account to get started" : "Sign in to your account to continue"}
        </p>
      </div>

      {/* Google Sign In */}
      <Button
        onClick={handleGoogleSignIn}
        disabled={isLoading}
        className="w-full bg-white text-gray-900 hover:bg-gray-50 border-2 border-gray-300 font-semibold py-3 rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
        size="lg"
      >
        <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          />
        </svg>
        {isLoading ? "Signing in..." : "Sign in with Google"}
      </Button>

      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-gray-300" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-white px-4 text-gray-500 font-medium">
            Or continue with email
          </span>
        </div>
      </div>

      {/* Error Message (if any) */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Email/Password Form */}
      <form onSubmit={handleEmailAuth} className="space-y-4">
        {isSignUp && (
          <div className="space-y-2">
            <label htmlFor="name" className="text-sm font-medium text-gray-700">
              Full Name
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                id="name"
                type="text"
                placeholder="John Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                required={isSignUp}
              />
            </div>
          </div>
        )}

        <div className="space-y-2">
          <label htmlFor="email" className="text-sm font-medium text-gray-700">
            Email
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              required
            />
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor="password" className="text-sm font-medium text-gray-700">
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              id="password"
              type="password"
              placeholder={isSignUp ? "Create a strong password" : "Enter your password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`w-full pl-10 pr-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all ${
                isSignUp && password && !isPasswordValid
                  ? "border-red-300"
                  : "border-gray-300"
              }`}
              required
            />
          </div>
          
          {/* Password Requirements (only show during sign-up) */}
          {isSignUp && password && (
            <div className="mt-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
              <p className="text-xs font-medium text-gray-700 mb-2">Password requirements:</p>
              <ul className="space-y-1.5 text-xs">
                <li className={`flex items-center ${passwordRequirements.minLength ? "text-green-600" : "text-gray-500"}`}>
                  {passwordRequirements.minLength ? (
                    <CheckCircle2 className="h-3 w-3 mr-2" />
                  ) : (
                    <X className="h-3 w-3 mr-2" />
                  )}
                  At least 8 characters
                </li>
                <li className={`flex items-center ${passwordRequirements.hasUpperCase ? "text-green-600" : "text-gray-500"}`}>
                  {passwordRequirements.hasUpperCase ? (
                    <CheckCircle2 className="h-3 w-3 mr-2" />
                  ) : (
                    <X className="h-3 w-3 mr-2" />
                  )}
                  One uppercase letter
                </li>
                <li className={`flex items-center ${passwordRequirements.hasLowerCase ? "text-green-600" : "text-gray-500"}`}>
                  {passwordRequirements.hasLowerCase ? (
                    <CheckCircle2 className="h-3 w-3 mr-2" />
                  ) : (
                    <X className="h-3 w-3 mr-2" />
                  )}
                  One lowercase letter
                </li>
                <li className={`flex items-center ${passwordRequirements.hasNumber ? "text-green-600" : "text-gray-500"}`}>
                  {passwordRequirements.hasNumber ? (
                    <CheckCircle2 className="h-3 w-3 mr-2" />
                  ) : (
                    <X className="h-3 w-3 mr-2" />
                  )}
                  One number
                </li>
                <li className={`flex items-center ${passwordRequirements.hasSpecialChar ? "text-green-600" : "text-gray-500"}`}>
                  {passwordRequirements.hasSpecialChar ? (
                    <CheckCircle2 className="h-3 w-3 mr-2" />
                  ) : (
                    <X className="h-3 w-3 mr-2" />
                  )}
                  One special character
                </li>
              </ul>
            </div>
          )}
        </div>

        {/* Confirm Password (only for sign-up) */}
        {isSignUp && (
          <div className="space-y-2">
            <label htmlFor="confirmPassword" className="text-sm font-medium text-gray-700">
              Confirm Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                id="confirmPassword"
                type="password"
                placeholder="Confirm your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`w-full pl-10 pr-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all ${
                  confirmPassword && !passwordsMatch
                    ? "border-red-300"
                    : confirmPassword && passwordsMatch
                    ? "border-green-300"
                    : "border-gray-300"
                }`}
                required={isSignUp}
              />
            </div>
            {confirmPassword && !passwordsMatch && (
              <p className="text-xs text-red-600 mt-1">Passwords do not match</p>
            )}
            {confirmPassword && passwordsMatch && (
              <p className="text-xs text-green-600 mt-1">Passwords match</p>
            )}
          </div>
        )}

        <Button
          type="submit"
          disabled={
            isLoading ||
            !email ||
            !password ||
            (isSignUp && (!name || !isPasswordValid || !passwordsMatch || !confirmPassword))
          }
          className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-3 rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
          size="lg"
        >
          {isLoading
            ? isSignUp
              ? "Creating account..."
              : "Signing in..."
            : isSignUp
            ? "Create account"
            : "Sign in"}
        </Button>

        <div className="text-center">
          <button
            type="button"
            onClick={() => {
              setIsSignUp(!isSignUp)
              setError(null)
              setPassword("")
              setConfirmPassword("")
            }}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            {isSignUp
              ? "Already have an account? Sign in"
              : "Don't have an account? Sign up"}
          </button>
        </div>
      </form>
    </div>
  )
}
