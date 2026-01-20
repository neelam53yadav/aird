"use client"

import { AuthButtons } from "@/components/AuthButtons"
import { ArrowLeft } from "lucide-react"
import Link from "next/link"

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-white to-rose-100 flex flex-col">

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Logo/Brand Section */}
          <div className="text-center mb-8">
            <Link href="/" className="inline-block mb-6" aria-label="Go to PrimeData homepage">
              <h1 className="text-5xl md:text-6xl font-bold mb-2">
                <span className="text-[#C8102E]">
                  PrimeData
                </span>
              </h1>
              <p className="text-sm text-gray-500 mt-1">Making Data AI-Ready</p>
            </Link>
          </div>

          {/* Back to Home Button */}
          <div className="mb-4">
            <Link
              href="/"
              className="inline-flex items-center text-sm text-[#C8102E] hover:text-[#A00D24] transition-colors"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Home
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
              <Link href="/terms" className="text-[#C8102E] hover:text-[#A00D24] font-medium transition-colors">
                Terms of Service
              </Link>
              {" "}and{" "}
              <Link href="/privacy" className="text-[#C8102E] hover:text-[#A00D24] font-medium transition-colors">
                Privacy Policy
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
