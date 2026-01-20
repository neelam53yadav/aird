'use client'

import { useState, useEffect, FormEvent } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Footer } from '@/components/Footer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { getApiUrl } from '@/lib/config'
import { Lock, ArrowLeft, CheckCircle2, AlertCircle, Eye, EyeOff } from 'lucide-react'

export default function ResetPasswordPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const token = searchParams.get('token')

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [status, setStatus] = useState<{
    type: 'success' | 'error' | null
    message: string
  }>({ type: null, message: '' })

  useEffect(() => {
    if (!token) {
      setStatus({
        type: 'error',
        message: 'Invalid reset link. Please request a new password reset.',
      })
    }
  }, [token])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()

    if (!token) {
      setStatus({
        type: 'error',
        message: 'Invalid reset link. Please request a new password reset.',
      })
      return
    }

    if (!password || !confirmPassword) {
      setStatus({ type: 'error', message: 'Please fill in all fields' })
      return
    }

    if (password.length < 8) {
      setStatus({ type: 'error', message: 'Password must be at least 8 characters long' })
      return
    }

    if (password !== confirmPassword) {
      setStatus({ type: 'error', message: 'Passwords do not match' })
      return
    }

    setSubmitting(true)
    setStatus({ type: null, message: '' })

    try {
      const apiUrl = getApiUrl()
      const response = await fetch(`${apiUrl}/api/v1/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          new_password: password,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        setStatus({
          type: 'error',
          message: data.detail || 'Failed to reset password. Please try again.',
        })
      } else {
        setStatus({
          type: 'success',
          message: data.message || 'Password reset successfully!',
        })
        // Redirect to sign-in after 3 seconds
        setTimeout(() => {
          router.push('/signin')
        }, 3000)
      }
    } catch (error) {
      console.error('Reset password error:', error)
      setStatus({
        type: 'error',
        message: 'An error occurred. Please try again later.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-white to-rose-100 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-4 py-4">
          <Link href="/signin" className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors">
            <ArrowLeft className="h-5 w-5" />
            <span className="text-sm">Back to Sign In</span>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl shadow-2xl border-2 border-gray-100 p-8">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-[#C8102E] to-[#A00D24] rounded-full mb-4">
                <Lock className="h-8 w-8 text-white" />
              </div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Reset Your Password</h1>
              <p className="text-gray-600">Enter your new password below.</p>
            </div>

            {/* Status Message */}
            {status.type && (
              <div
                className={`mb-6 p-4 rounded-lg flex items-start space-x-3 ${
                  status.type === 'success'
                    ? 'bg-green-50 border border-green-200'
                    : 'bg-red-50 border border-red-200'
                }`}
              >
                {status.type === 'success' ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                )}
                <p
                  className={`text-sm font-medium ${
                    status.type === 'success' ? 'text-green-800' : 'text-red-800'
                  }`}
                >
                  {status.message}
                </p>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <Label htmlFor="password" className="text-gray-700 font-medium">
                  New Password
                </Label>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10 pr-10"
                    placeholder="Enter new password"
                    disabled={submitting || !token}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
                <p className="mt-1 text-xs text-gray-500">Must be at least 8 characters long</p>
              </div>

              <div>
                <Label htmlFor="confirmPassword" className="text-gray-700 font-medium">
                  Confirm New Password
                </Label>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="pl-10 pr-10"
                    placeholder="Confirm new password"
                    disabled={submitting || !token}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
                {confirmPassword && password !== confirmPassword && (
                  <p className="mt-1 text-xs text-red-600">Passwords do not match</p>
                )}
              </div>

              <Button
                type="submit"
                disabled={submitting || !token || password !== confirmPassword}
                className="w-full bg-[#C8102E] hover:bg-[#A00D24] text-white font-semibold py-3 rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
              >
                {submitting ? 'Resetting Password...' : 'Reset Password'}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <Link
                href="/signin"
                className="text-sm text-[#C8102E] hover:text-[#A00D24] font-medium transition-colors"
              >
                Back to Sign In
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  )
}

