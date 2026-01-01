"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { CheckCircle2, XCircle, Mail, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { getApiUrl } from "@/lib/config"

export default function VerifyEmailPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get("token")
  
  const [status, setStatus] = useState<"verifying" | "success" | "error" | "expired">("verifying")
  const [message, setMessage] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const isVerifyingRef = useRef(false)

  useEffect(() => {
    if (!token) {
      setStatus("error")
      setMessage("No verification token provided")
      setIsLoading(false)
      return
    }

    verifyEmail(token)
  }, [token])

  const verifyEmail = async (verificationToken: string) => {
    // Prevent duplicate requests
    if (isVerifyingRef.current) {
      return
    }
    
    isVerifyingRef.current = true
    
    try {
      const apiUrl = getApiUrl()
      const response = await fetch(`${apiUrl}/api/v1/auth/verify-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: verificationToken }),
      })

      if (!response.ok) {
        const error = await response.json()
        if (error.detail?.includes("expired")) {
          setStatus("expired")
          setMessage(error.detail)
        } else {
          setStatus("error")
          setMessage(error.detail || "Verification failed")
        }
        return
      }

      const data = await response.json()
      setStatus("success")
      setMessage(data.message || "Email verified successfully")
    } catch (error) {
      setStatus("error")
      setMessage("An error occurred while verifying your email. Please try again.")
    } finally {
      setIsLoading(false)
      isVerifyingRef.current = false
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-2xl border-2 border-gray-100 p-8">
          {isLoading ? (
            <div className="text-center">
              <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Verifying your email...</h2>
              <p className="text-gray-600">Please wait while we verify your email address.</p>
            </div>
          ) : status === "success" ? (
            <div className="text-center">
              <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Email Verified!</h2>
              <p className="text-gray-600 mb-6">{message}</p>
              <Button
                onClick={() => router.push("/signin")}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-3 rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
              >
                Sign In
              </Button>
            </div>
          ) : status === "expired" ? (
            <div className="text-center">
              <XCircle className="h-16 w-16 text-orange-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Verification Link Expired</h2>
              <p className="text-gray-600 mb-6">{message}</p>
              <div className="space-y-3">
                <Button
                  onClick={() => router.push("/signin")}
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-3 rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
                >
                  Go to Sign In
                </Button>
                <p className="text-sm text-gray-500">
                  You can request a new verification email from the sign-in page.
                </p>
              </div>
            </div>
          ) : (
            <div className="text-center">
              <XCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Verification Failed</h2>
              <p className="text-gray-600 mb-6">{message}</p>
              <div className="space-y-3">
                <Button
                  onClick={() => router.push("/signin")}
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-3 rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
                >
                  Go to Sign In
                </Button>
                <Link
                  href="/"
                  className="block text-center text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
                >
                  Back to Home
                </Link>
              </div>
            </div>
          )}
        </div>
        
        <div className="mt-6 text-center">
          <Link
            href="/"
            className="inline-block text-2xl font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent hover:from-blue-500 hover:via-indigo-500 hover:to-purple-500 transition-all duration-200"
          >
            PrimeData
          </Link>
        </div>
      </div>
    </div>
  )
}

