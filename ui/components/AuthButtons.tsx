"use client"

import { useState } from "react"
import { signIn } from "next-auth/react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "./ui/button"
import { exchangeToken } from "@/lib/auth-utils"
import { getApiUrl } from "@/lib/config"
import { apiClient } from "@/lib/api-client"
import { Mail, Lock, User, CheckCircle2, X, RefreshCw } from "lucide-react"

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
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isSignUp, setIsSignUp] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [signupSuccess, setSignupSuccess] = useState(false)
  const [showResendVerification, setShowResendVerification] = useState(false)
  const [resendLoading, setResendLoading] = useState(false)
  const [resendSuccess, setResendSuccess] = useState(false)
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

  // Email format validation
  const validateEmailFormat = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  // Validate email domain (check if domain exists)
  const validateEmailDomain = async (email: string): Promise<{ valid: boolean; message?: string }> => {
    if (!validateEmailFormat(email)) {
      return { valid: false, message: "Please enter a valid email address" }
    }

    try {
      const apiUrl = getApiUrl()
      const response = await fetch(`${apiUrl}/api/v1/auth/validate-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })

      if (!response.ok) {
        const error = await response.json()
        return { valid: false, message: error.detail || "Email validation failed" }
      }

      const data = await response.json()
      return { valid: data.valid, message: data.message }
    } catch (error) {
      console.error("Email validation error:", error)
      return { valid: false, message: "Unable to validate email. Please try again." }
    }
  }

  // Handle email change (no real-time validation)
  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEmail(e.target.value)
  }

  const handleSSOSignIn = async () => {
    // SSO login is currently disabled
    setError("SSO login is currently unavailable. Please use email/password authentication.")
  }

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSignupSuccess(false)
    
    if (!email || !password) {
      setError("Please fill in all fields")
      return
    }

    // Validate email format
    if (!validateEmailFormat(email)) {
      setError("Please enter a valid email address")
      return
    }
    
    if (isSignUp) {
      if (!firstName || !lastName) {
        setError("Please enter your first and last name")
        return
      }

      // Validate email domain for sign-up
      const emailValidation = await validateEmailDomain(email)
      
      if (!emailValidation.valid) {
        setError(emailValidation.message || "Invalid email address")
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
      const apiUrl = getApiUrl()

      if (isSignUp) {
        // Sign up with email/password
        const response = await fetch(`${apiUrl}/api/v1/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password, first_name: firstName, last_name: lastName }),
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || "Sign up failed")
        }

        const data = await response.json()

        // Check if verification is required
        if (data.requires_verification) {
          setSignupSuccess(true)
          setIsLoading(false)
          return // Don't sign in yet, user needs to verify email
        }

        // If verification not required (shouldn't happen), sign in
        const result = await signIn("credentials", {
          email,
          password,
          redirect: false,
        })

        if (result?.ok) {
          await exchangeToken()
          await new Promise((resolve) => setTimeout(resolve, 100))
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
          await exchangeToken()
          await new Promise((resolve) => setTimeout(resolve, 100))
          router.push("/dashboard")
        } else {
          throw new Error(result?.error || "Sign in failed")
        }
      }
    } catch (error) {
      // Extract error message from NextAuth error
      let errorMessage = "Authentication failed"
      
      if (error instanceof Error) {
        errorMessage = error.message
      } else if (typeof error === "string") {
        errorMessage = error
      } else if (error && typeof error === "object" && "message" in error) {
        errorMessage = String(error.message)
      }
      
      // Show user-friendly error messages
      if (errorMessage.includes("Invalid email or password") || 
          errorMessage.includes("Invalid email") || 
          errorMessage.includes("Invalid password")) {
        setError("Invalid email or password. Please check your credentials and try again.")
        setShowResendVerification(false)
      } else if (errorMessage.includes("verify your email address") || 
                 errorMessage.includes("verification link has expired")) {
        // Show resend verification button for unverified email errors
        setError(errorMessage)
        setShowResendVerification(true)
      } else if (errorMessage.includes("Email and password are required")) {
        setError("Please enter both email and password")
        setShowResendVerification(false)
      } else if (errorMessage.includes("fetch failed") || errorMessage.includes("Failed to fetch")) {
        setError("Unable to connect to the server. Please check your connection and try again.")
        setShowResendVerification(false)
      } else {
        setError(errorMessage)
        setShowResendVerification(false)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleResendVerification = async () => {
    if (!email.trim()) {
      setError("Please enter your email address first")
      return
    }

    setResendLoading(true)
    setResendSuccess(false)
    setError(null)

    try {
      const response = await apiClient.resendVerification(email.trim())
      
      if (response.error) {
        setError(response.error || "Failed to send verification email. Please try again.")
        setResendSuccess(false)
      } else if (response.data) {
        setResendSuccess(true)
        setError(null)
        setShowResendVerification(false)
        // Clear success message after 5 seconds
        setTimeout(() => {
          setResendSuccess(false)
        }, 5000)
      } else {
        setError("An unexpected error occurred. Please try again.")
        setResendSuccess(false)
      }
    } catch (error) {
      console.error("Resend verification error:", error)
      setError("An error occurred while sending the verification email. Please try again later.")
      setResendSuccess(false)
    } finally {
      setResendLoading(false)
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

      {/* SSO Sign In */}
      <Button
        onClick={handleSSOSignIn}
        disabled={true}
        className="w-full bg-gray-100 text-gray-500 border-2 border-gray-300 font-semibold py-3 rounded-lg shadow-md cursor-not-allowed opacity-60"
        size="lg"
      >
        <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
        </svg>
        SSO Login (Coming Soon)
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

      {/* Success Message (for signup) */}
      {signupSuccess && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
          <p className="font-semibold mb-2">Account created successfully!</p>
          <p>Please check your email ({email}) to verify your account before signing in.</p>
        </div>
      )}

      {/* Error Message (if any) */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          <p>{error}</p>
          {/* Resend Verification Button */}
          {showResendVerification && !resendSuccess && (
            <button
              type="button"
              onClick={handleResendVerification}
              disabled={resendLoading}
              className="mt-3 w-full text-left text-red-700 hover:text-red-900 font-medium underline disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {resendLoading ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Mail className="h-4 w-4" />
                  Resend Verification Email
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Resend Verification Success Message */}
      {resendSuccess && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
          <p className="font-semibold">Verification email sent!</p>
          <p className="mt-1">Please check your inbox and click the verification link to activate your account.</p>
        </div>
      )}

      {/* Email/Password Form - Hide on successful signup, show on error or sign in */}
      {!(signupSuccess && isSignUp) && (
        <form onSubmit={handleEmailAuth} className="space-y-4">
        {isSignUp && (
          <>
            <div className="space-y-2">
              <label htmlFor="firstName" className="text-sm font-medium text-gray-700">
                First Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  id="firstName"
                  type="text"
                  placeholder="John"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  required={isSignUp}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="lastName" className="text-sm font-medium text-gray-700">
                Last Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  id="lastName"
                  type="text"
                  placeholder="Doe"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  required={isSignUp}
                />
              </div>
            </div>
          </>
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
              onChange={handleEmailChange}
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
            (isSignUp && (!firstName || !lastName || !isPasswordValid || !passwordsMatch || !confirmPassword))
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

        <div className="text-center space-y-2">
          {!isSignUp && (
            <div>
              <Link
                href="/forgot-password"
                className="text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
              >
                Forgot your password?
              </Link>
            </div>
          )}
            <button
              type="button"
              onClick={() => {
                setIsSignUp(!isSignUp)
                setError(null)
                setPassword("")
                setConfirmPassword("")
                setFirstName("")
                setLastName("")
                setEmail("")
                setShowResendVerification(false)
                setResendSuccess(false)
                setSignupSuccess(false)  // Clear success state when toggling
              }}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
            >
              {isSignUp
                ? "Already have an account? Sign in"
                : "Don't have an account? Sign up"}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
