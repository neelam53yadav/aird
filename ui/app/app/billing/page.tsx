'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { CreditCard, CheckCircle, XCircle } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import AppLayout from '@/components/layout/AppLayout'
import { useSession } from 'next-auth/react'

export default function BillingPage() {
  const { data: session } = useSession()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  // Get workspace ID from session or use default for testing
  const workspaceId = session?.user?.workspace_ids?.[0] || '550e8400-e29b-41d4-a716-446655440001'

  useEffect(() => {
    if (workspaceId) {
      loadBillingLimits()
    }
  }, [workspaceId])

  const loadBillingLimits = async () => {
    try {
      setLoading(true)
      const response = await apiClient.get(`/api/v1/billing/limits?workspace_id=${workspaceId}`)
      console.log('Billing limits response:', response.data)
    } catch (err) {
      console.error('Failed to load billing limits:', err)
      setError('Failed to load billing information')
    } finally {
      setLoading(false)
    }
  }

  const handleUpgrade = async (plan: string) => {
    console.log(`Upgrading to ${plan} plan`)
    setMessage(`Redirecting to ${plan} plan checkout... This would open Stripe checkout in a real implementation.`)
    
    // Clear message after 5 seconds
    setTimeout(() => {
      setMessage(null)
    }, 5000)
  }

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </AppLayout>
    )
  }

  if (!workspaceId) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-gray-900 mb-2">No Workspace</h2>
            <p className="text-gray-600 mb-4">Please create a workspace to manage billing.</p>
          </div>
        </div>
      </AppLayout>
    )
  }

  if (error) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Error</h2>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button onClick={loadBillingLimits}>Try Again</Button>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900">Billing & Usage</h1>
        <p className="text-gray-600 mt-2">Manage your subscription and monitor usage</p>
        
        {/* Message Display */}
        {message && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
            <div className="flex">
              <div className="flex-shrink-0">
                <CheckCircle className="h-5 w-5 text-blue-400" />
              </div>
              <div className="ml-3">
                <p className="text-sm text-blue-800">{message}</p>
              </div>
            </div>
          </div>
        )}
        
        {/* Plan Comparison */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          {/* Free Plan */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Free</h3>
              <p className="text-sm text-gray-600 mt-1">Perfect for getting started</p>
            </div>
            <div className="px-6 py-4">
              <div className="text-2xl font-bold text-gray-900 mb-4">$0<span className="text-sm font-normal text-gray-600">/month</span></div>
              <ul className="space-y-3 text-sm">
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Up to 3 products</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>5 data sources per product</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>10 pipeline runs per month</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>10,000 vectors</span>
                </li>
              </ul>
              <div className="mt-6">
                <Button className="w-full" variant="secondary">
                  Current Plan
                </Button>
              </div>
            </div>
          </div>

          {/* Pro Plan */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Pro</h3>
              <p className="text-sm text-gray-600 mt-1">For growing teams</p>
            </div>
            <div className="px-6 py-4">
              <div className="text-2xl font-bold text-gray-900 mb-4">$99<span className="text-sm font-normal text-gray-600">/month</span></div>
              <ul className="space-y-3 text-sm">
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Up to 25 products</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>50 data sources per product</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>1,000 pipeline runs per month</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>1,000,000 vectors</span>
                </li>
              </ul>
              <div className="mt-6">
                <Button 
                  className="w-full" 
                  onClick={() => handleUpgrade('pro')}
                >
                  Upgrade to Pro
                </Button>
              </div>
            </div>
          </div>

          {/* Enterprise Plan */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Enterprise</h3>
              <p className="text-sm text-gray-600 mt-1">For large organizations</p>
            </div>
            <div className="px-6 py-4">
              <div className="text-2xl font-bold text-gray-900 mb-4">$299<span className="text-sm font-normal text-gray-600">/month</span></div>
              <ul className="space-y-3 text-sm">
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Unlimited products</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Unlimited data sources</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Unlimited pipeline runs</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Unlimited vectors</span>
                </li>
              </ul>
              <div className="mt-6">
                <Button 
                  className="w-full" 
                  onClick={() => handleUpgrade('enterprise')}
                >
                  Upgrade to Enterprise
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
