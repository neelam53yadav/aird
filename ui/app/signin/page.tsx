"use client"

import { AuthButtons } from "@/components/AuthButtons"
import { Sparkles } from "lucide-react"
import Link from "next/link"

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex flex-col">
      {/* Beta Badge - Top Banner */}
      <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white py-2" role="banner">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-center space-x-2" aria-live="polite">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            <span className="text-sm font-medium">
              AIRDOps Beta Release - We're actively improving based on your feedback
            </span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Logo/Brand Section */}
          <div className="text-center mb-8">
            <Link href="/" className="inline-block mb-6" aria-label="Go to AIRDOps homepage">
              <h1 className="text-5xl md:text-6xl font-bold mb-2">
                <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
                  AIRDOps
                </span>
              </h1>
              <p className="text-sm text-gray-500 mt-1">Making Data AI-Ready</p>
            </Link>
          </div>

          {/* Auth Card */}
          <div className="bg-white rounded-2xl shadow-2xl border-2 border-gray-100 p-8">
            <AuthButtons />
          </div>

          {/* Footer Links */}
          <div className="mt-8 text-center">
            <p className="text-sm text-gray-500">
              By signing in, you agree to our{" "}
              <Link href="/terms" className="text-blue-600 hover:text-blue-700 font-medium transition-colors">
                Terms of Service
              </Link>
              {" "}and{" "}
              <Link href="/privacy" className="text-blue-600 hover:text-blue-700 font-medium transition-colors">
                Privacy Policy
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
