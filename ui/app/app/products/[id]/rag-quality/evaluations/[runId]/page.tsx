'use client'

import { useState, useEffect, useRef } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Download, CheckCircle2, XCircle, BarChart3, Loader2, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient } from '@/lib/api-client'
import { CardSkeleton } from '@/components/ui/skeleton'
import { StatusBadge } from '@/components/ui/status-badge'

interface EvaluationRun {
  id: string
  product_id: string
  version: number
  status: string
  metrics?: {
    aggregate?: Record<string, {
      mean: number
      min: number
      max: number
      count: number
    }>
    per_query?: Array<{
      item_id: string
      query: string
      metrics: Record<string, {
        score: number
        passed: boolean
        details?: any
      }>
      error?: string
    }>
  }
  started_at?: string
  finished_at?: string
  created_at: string
  report_path?: string
}

// Map evaluation status to StatusBadge status type
const mapEvaluationStatus = (status: string): 'queued' | 'running' | 'succeeded' | 'failed' => {
  switch (status) {
    case 'pending':
    case 'queued':
      return 'queued'
    case 'running':
      return 'running'
    case 'completed':
      return 'succeeded'
    case 'failed':
      return 'failed'
    default:
      return 'queued'
  }
}

export default function EvaluationRunDetailPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const params = useParams()
  const productId = params.id as string
  const runId = params.runId as string

  const [run, setRun] = useState<EvaluationRun | null>(null)
  const [loading, setLoading] = useState(true)
  const [downloadingReport, setDownloadingReport] = useState(false)
  const [polling, setPolling] = useState(false)
  
  // Ref to track the polling interval
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (status === 'authenticated' && runId) {
      loadData()
    }
  }, [status, runId])

  // Auto-refresh if evaluation is running
  useEffect(() => {
    const isRunning = run?.status === 'running' || run?.status === 'queued' || run?.status === 'pending'
    
    if (isRunning && !intervalRef.current) {
      setPolling(true)
      intervalRef.current = setInterval(() => {
        loadData(false)
      }, 10000) // Poll every 10 seconds
    } else if (!isRunning && intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
      setPolling(false)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [run?.status])

  const loadData = async (showLoading = true) => {
    if (showLoading) setLoading(true)
    try {
      const response = await apiClient.getEvaluationRun(runId)
      if (!response.error && response.data) {
        setRun(response.data as EvaluationRun)
      }
    } catch (err) {
      console.error('Failed to load evaluation run:', err)
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  const handleDownloadReport = async () => {
    setDownloadingReport(true)
    try {
      const blob = await apiClient.downloadEvaluationReport(runId)
      
      if (!blob) {
        throw new Error('Failed to download report')
      }

      // Determine file extension from report_path or default to csv
      const extension = run?.report_path?.endsWith('.csv') ? 'csv' : 
                      run?.report_path?.endsWith('.pdf') ? 'pdf' : 'csv'

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `evaluation-report-${runId}.${extension}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Failed to download report:', err)
      alert('Failed to download the evaluation report. Please try again later.')
    } finally {
      setDownloadingReport(false)
    }
  }

  if (loading) {
    return (
      <AppLayout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Breadcrumb Navigation */}
          <div className="flex items-center mb-6">
            <Link href={`/app/products/${productId}/rag-quality/evaluations`} className="flex items-center text-sm text-gray-600 hover:text-gray-900 transition-colors">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Evaluations
            </Link>
            <span className="mx-2 text-gray-400">/</span>
            <span className="text-sm font-medium text-gray-900">Run Details</span>
          </div>

          {/* Page Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900">Evaluation Run Details</h1>
          </div>

          <CardSkeleton />
        </div>
      </AppLayout>
    )
  }

  if (!run) {
    return (
      <AppLayout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Breadcrumb Navigation */}
          <div className="flex items-center mb-6">
            <Link href={`/app/products/${productId}/rag-quality/evaluations`} className="flex items-center text-sm text-gray-600 hover:text-gray-900 transition-colors">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Evaluations
            </Link>
            <span className="mx-2 text-gray-400">/</span>
            <span className="text-sm font-medium text-gray-900">Run Details</span>
          </div>

          {/* Page Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900">Evaluation Run Details</h1>
          </div>

          {/* Error Message */}
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <div className="flex items-start">
              <XCircle className="h-5 w-5 text-red-600 mr-3 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="text-lg font-semibold text-red-900 mb-2">Evaluation Run Not Found</h3>
                <p className="text-red-800 mb-4">
                  The evaluation run you're looking for doesn't exist or may have been deleted.
                </p>
                <Link href={`/app/products/${productId}/rag-quality/evaluations`}>
                  <Button variant="outline" className="flex items-center gap-2">
                    <ArrowLeft className="h-4 w-4" />
                    Back to Evaluations
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </AppLayout>
    )
  }

  const aggregate = run.metrics?.aggregate || {}
  const perQuery = run.metrics?.per_query || []
  const isRunning = run.status === 'running' || run.status === 'queued' || run.status === 'pending'
  const isCompleted = run.status === 'completed'

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center mb-6">
          <Link href={`/app/products/${productId}/rag-quality/evaluations`} className="flex items-center text-sm text-gray-600 hover:text-gray-900 transition-colors">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Evaluations
          </Link>
          <span className="mx-2 text-gray-400">/</span>
          <span className="text-sm font-medium text-gray-900">Run Details</span>
        </div>

        {/* Page Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Evaluation Run Details</h1>
            <p className="mt-2 text-sm text-gray-600">
              Version {run.version} • {new Date(run.created_at).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={mapEvaluationStatus(run.status)} />
            {isCompleted && run.report_path && (
              <Button 
                variant="outline"
                onClick={handleDownloadReport}
                disabled={downloadingReport}
                className="flex items-center gap-2"
              >
                {downloadingReport ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Downloading...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4" />
                    Download Report
                  </>
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Polling indicator */}
        {polling && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center gap-2">
            <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
            <span className="text-sm text-blue-800">Auto-refreshing evaluation status...</span>
          </div>
        )}

        {/* Running State - Progress Indicator */}
        {isRunning && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 mb-6">
            <div className="text-center">
              <div className="flex justify-center mb-4">
                <div className="relative">
                  <Activity className="h-16 w-16 text-blue-600 animate-pulse" />
                  <Loader2 className="h-8 w-8 text-blue-600 animate-spin absolute top-4 left-4" />
                </div>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Evaluation in Progress</h3>
              <p className="text-gray-600 mb-4">
                The evaluation is currently running. Results will be available when it completes.
              </p>
              {run.started_at && (
                <p className="text-sm text-gray-500">
                  Started: {new Date(run.started_at).toLocaleString()}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Aggregate Metrics */}
        {isCompleted && aggregate && Object.keys(aggregate).length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Aggregate Metrics</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {Object.entries(aggregate).map(([metricName, data]) => (
                <div key={metricName} className="border border-gray-200 rounded-lg p-4">
                  <p className="text-xs text-gray-500 mb-1 capitalize">{metricName.replace(/_/g, ' ')}</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {(data.mean * 100).toFixed(1)}%
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Min: {(data.min * 100).toFixed(1)}% • Max: {(data.max * 100).toFixed(1)}%
                  </p>
                  <p className="text-xs text-gray-500">Count: {data.count}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Per-Query Results */}
        {isCompleted && perQuery.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Per-Query Results</h2>
            </div>
            <div className="divide-y divide-gray-200">
              {perQuery.map((result, index) => (
                <div key={result.item_id || index} className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 mb-2">{result.query}</p>
                      {result.error ? (
                        <p className="text-sm text-red-600">Error: {result.error}</p>
                      ) : (
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                          {Object.entries(result.metrics || {}).map(([metricName, metricData]) => (
                            <div key={metricName} className="flex items-center">
                              {metricData.passed ? (
                                <CheckCircle2 className="h-4 w-4 text-green-600 mr-2" />
                              ) : (
                                <XCircle className="h-4 w-4 text-red-600 mr-2" />
                              )}
                              <div>
                                <p className="text-xs text-gray-500 capitalize">{metricName.replace(/_/g, ' ')}</p>
                                <p className="text-sm font-medium text-gray-900">
                                  {(metricData.score * 100).toFixed(1)}%
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State for non-completed runs */}
        {!isRunning && !isCompleted && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {run.status === 'failed' ? 'Evaluation Failed' : 'Evaluation Pending'}
            </h3>
            <p className="text-gray-600">
              {run.status === 'failed'
                ? 'The evaluation encountered an error. Please check the logs or try running again.'
                : 'The evaluation has not started yet.'}
            </p>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
