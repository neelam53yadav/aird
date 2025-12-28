'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, CheckCircle, XCircle, AlertCircle, RefreshCw, Activity, Database, Search, HardDrive, BarChart3, GitBranch } from 'lucide-react'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient, HealthCheckResponse } from '@/lib/api-client'
import { useToast } from '@/components/ui/toast'
import { Button } from '@/components/ui/button'

export default function SystemHealthPage() {
  const router = useRouter()
  const [health, setHealth] = useState<HealthCheckResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastChecked, setLastChecked] = useState<Date | null>(null)
  const { addToast } = useToast()

  const loadHealth = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.getHealthCheck()
      if (response.error) {
        setError(response.error)
        addToast({
          type: 'error',
          message: `Failed to load system health: ${response.error}`,
        })
      } else if (response.data) {
        setHealth(response.data)
        setLastChecked(new Date())
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load system health'
      setError(errorMessage)
      addToast({
        type: 'error',
        message: errorMessage,
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHealth()
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const getServiceIcon = (serviceName: string) => {
    switch (serviceName.toLowerCase()) {
      case 'database':
        return <Database className="h-5 w-5" />
      case 'qdrant':
        return <Search className="h-5 w-5" />
      case 'minio':
        return <HardDrive className="h-5 w-5" />
      case 'mlflow':
        return <BarChart3 className="h-5 w-5" />
      case 'airflow':
        return <GitBranch className="h-5 w-5" />
      default:
        return <Activity className="h-5 w-5" />
    }
  }

  const getServiceName = (serviceName: string) => {
    switch (serviceName.toLowerCase()) {
      case 'database':
        return 'PostgreSQL Database'
      case 'qdrant':
        return 'Qdrant Vector DB'
      case 'minio':
        return 'MinIO Object Storage'
      case 'mlflow':
        return 'MLflow Tracking'
      case 'airflow':
        return 'Apache Airflow'
      default:
        return serviceName
    }
  }

  return (
    <AppLayout>
      <div className="p-6">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center mb-6">
          <Link href="/app" className="flex items-center text-sm text-gray-500 hover:text-gray-700 transition-colors">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Dashboard
          </Link>
          <span className="mx-2 text-gray-400">/</span>
          <span className="text-sm font-medium text-gray-900">System Health</span>
        </div>

        {/* Page Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">System Health</h1>
            <p className="text-gray-600 mt-1">
              Monitor the health and status of all PrimeData services and dependencies.
            </p>
          </div>
          <Button
            variant="outline"
            onClick={loadHealth}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Overall Status */}
        {health && (
          <div className={`mb-6 rounded-lg border p-6 ${
            health.status === 'healthy'
              ? 'bg-green-50 border-green-200'
              : 'bg-yellow-50 border-yellow-200'
          }`}>
            <div className="flex items-center gap-3">
              {health.status === 'healthy' ? (
                <CheckCircle className="h-8 w-8 text-green-600" />
              ) : (
                <AlertCircle className="h-8 w-8 text-yellow-600" />
              )}
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  System Status: {health.status === 'healthy' ? 'All Systems Operational' : 'Degraded'}
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Service: {health.service} v{health.version}
                  {lastChecked && (
                    <span className="ml-2">
                      • Last checked: {lastChecked.toLocaleTimeString()}
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && !health && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading system health status...</p>
          </div>
        )}

        {/* Error State */}
        {error && !health && (
          <div className="bg-white rounded-lg shadow-sm border border-red-200 p-6">
            <div className="flex items-center gap-3">
              <XCircle className="h-6 w-6 text-red-500" />
              <div>
                <h3 className="text-lg font-semibold text-red-900">Failed to Load Health Status</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Services Status */}
        {health && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(health.services).map(([serviceName, serviceStatus]) => (
              <div
                key={serviceName}
                className={`bg-white rounded-lg shadow-sm border p-6 ${
                  (serviceStatus as any).status === 'healthy'
                    ? 'border-green-200'
                    : 'border-red-200'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${
                      (serviceStatus as any).status === 'healthy'
                        ? 'bg-green-100 text-green-600'
                        : 'bg-red-100 text-red-600'
                    }`}>
                      {getServiceIcon(serviceName)}
                    </div>
                    <div>
                      <h3 className="text-md font-semibold text-gray-900">
                        {getServiceName(serviceName)}
                      </h3>
                      <p className="text-xs text-gray-500 mt-0.5">{serviceName}</p>
                    </div>
                  </div>
                  {(serviceStatus as any).status === 'healthy' ? (
                    <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
                  )}
                </div>
                <div className={`mt-3 p-3 rounded-lg ${
                  (serviceStatus as any).status === 'healthy'
                    ? 'bg-green-50'
                    : 'bg-red-50'
                }`}>
                  <p className={`text-sm font-medium ${
                    (serviceStatus as any).status === 'healthy'
                      ? 'text-green-800'
                      : 'text-red-800'
                  }`}>
                    {(serviceStatus as any).status === 'healthy' ? 'Operational' : 'Unavailable'}
                  </p>
                  <p className={`text-xs mt-1 ${
                    (serviceStatus as any).status === 'healthy'
                      ? 'text-green-700'
                      : 'text-red-700'
                  }`}>
                    {(serviceStatus as any).message}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Additional Information */}
        {health && (
          <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-md font-semibold text-gray-900 mb-3">System Information</h3>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">Service Name</dt>
                <dd className="mt-1 text-sm text-gray-900">{health.service}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Version</dt>
                <dd className="mt-1 text-sm text-gray-900">{health.version}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Overall Status</dt>
                <dd className="mt-1">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    health.status === 'healthy'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {health.status}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Last Check</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {lastChecked ? lastChecked.toLocaleString() : 'Never'}
                </dd>
              </div>
            </dl>
          </div>
        )}
      </div>
    </AppLayout>
  )
}




