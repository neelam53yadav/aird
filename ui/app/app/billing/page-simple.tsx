'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { CreditCard, CheckCircle, XCircle } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import AppLayout from '@/components/layout/AppLayout'
import { useSession } from 'next-auth/react'

export default function BillingPageSimple() {
  const { data: session } = useSession()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
        
        <div className="mt-8">
          <Button>Test Button</Button>
        </div>
      </div>
    </AppLayout>
  )
}
