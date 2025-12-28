'use client'

import { useState, useEffect } from 'react'
import { signIn, useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { AuthButtons } from '@/components/AuthButtons'
import { exchangeToken } from '@/lib/auth-utils'

export default function HomePage() {
  const router = useRouter()
  const { data: session, status } = useSession()

  // Redirect to dashboard if user is already authenticated
  useEffect(() => {
    if (status === 'authenticated' && session) {
      console.log("User is authenticated, exchanging token and redirecting to dashboard")
      // Exchange token to register user in backend
      exchangeToken().then(() => {
        router.push('/dashboard')
      }).catch((error) => {
        console.error("Token exchange failed:", error)
        // Still redirect even if exchange fails
        router.push('/dashboard')
      })
    }
  }, [session, status, router])

  const handleGoogleSignIn = async () => {
    console.log("Starting Google sign in...")
    try {
      const result = await signIn("google", { 
        callbackUrl: "/dashboard",
        redirect: false // Don't redirect automatically, we'll handle it manually
      })
      console.log("Sign in result:", result)
      
      if (result?.ok) {
        console.log("Sign in successful, exchanging token...")
        // Exchange token to register user in backend
        const exchangeSuccess = await exchangeToken()
        if (exchangeSuccess) {
          console.log("Token exchange successful, redirecting to dashboard")
        } else {
          console.warn("Token exchange failed, but continuing with redirect")
        }
        router.push('/dashboard')
      } else if (result?.error) {
        console.error("Sign in error:", result.error)
      }
    } catch (error) {
      console.error("Sign in error:", error)
    }
  }

  const handleEmailSignIn = () => {
    router.push("/signin")
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            PrimeData — AI-ready data from any source
          </h1>
          <p className="text-xl text-gray-600 mb-12 leading-relaxed">
            Ingest, clean, chunk, embed & index. Test and export with confidence.
          </p>
          
          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
            <button
              data-testid="cta-google"
              onClick={handleGoogleSignIn}
              className="bg-white hover:bg-gray-50 text-gray-900 font-semibold py-3 px-8 rounded-lg border border-gray-300 shadow-sm transition-all duration-200 hover:shadow-md"
            >
              Sign in with Google
            </button>
            
            <button
              data-testid="cta-email"
              onClick={handleEmailSignIn}
              className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-8 rounded-lg shadow-sm transition-all duration-200 hover:shadow-md"
            >
              Continue with email
            </button>
          </div>
        </div>

        {/* Feature Tiles */}
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* Connectors */}
          <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow duration-200">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-6">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Connectors</h3>
            <p className="text-gray-600 leading-relaxed">
              Seamlessly ingest data from files, APIs, databases, and cloud storage. 
              Built-in connectors for popular data sources with real-time sync capabilities.
            </p>
          </div>

          {/* Orchestrate with Airflow */}
          <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow duration-200">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-6">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Orchestrate with Airflow</h3>
            <p className="text-gray-600 leading-relaxed">
              Powerful data pipeline orchestration with Apache Airflow. 
              Schedule, monitor, and manage complex data workflows with visual DAGs.
            </p>
          </div>

          {/* Evaluate & Export */}
          <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow duration-200">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-6">
              <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Evaluate & Export</h3>
            <p className="text-gray-600 leading-relaxed">
              Test your data quality and AI models with comprehensive evaluation tools. 
              Export processed data in multiple formats for downstream applications.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
