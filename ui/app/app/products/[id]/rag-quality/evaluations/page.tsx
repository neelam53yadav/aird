'use client'

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import React from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Play, BarChart3, Download, Eye, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ResultModal, ConfirmModal } from '@/components/ui/modal'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient } from '@/lib/api-client'
import { CardSkeleton } from '@/components/ui/skeleton'
import { StatusBadge } from '@/components/ui/status-badge'

interface Product {
  id: string
  name: string
  current_version: number
}

interface EvaluationDataset {
  id: string
  name: string
  dataset_type: string
}

interface EvaluationRun {
  id: string
  product_id: string
  version: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'queued'
  metrics?: {
    aggregate?: Record<string, {
      mean: number
      min: number
      max: number
      count: number
    }>
    per_query?: Array<{
      query: string
      metrics: Record<string, any>
    }>
  }
  started_at?: string
  finished_at?: string
  created_at: string
  report_path?: string
  dag_run_id?: string | null
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

export default function EvaluationsPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const params = useParams()
  const productId = params.id as string

  const [product, setProduct] = useState<Product | null>(null)
  const [datasets, setDatasets] = useState<EvaluationDataset[]>([])
  const [runs, setRuns] = useState<EvaluationRun[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [selectedDataset, setSelectedDataset] = useState<string>('')
  const [polling, setPolling] = useState(false)
  const [downloadingReport, setDownloadingReport] = useState<string | null>(null)

  // Ref to track the polling interval
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  // Ref to track latest runs state for checking inside interval callback
  const runsRef = useRef<EvaluationRun[]>([])
  // State for current time to update duration in real-time
  const [currentTime, setCurrentTime] = useState(new Date())
  // Ref to track the duration update interval
  const durationIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const [showResultModal, setShowResultModal] = useState(false)
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [resultModalData, setResultModalData] = useState<{
    type: 'success' | 'error' | 'warning' | 'info'
    title: string
    message: string
    actionButton?: {
      label: string
      onClick: () => void
      variant?: 'primary' | 'secondary'
    }
  } | null>(null)

  const loadData = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true)
    try {
      const productResponse = await apiClient.getProduct(productId)
      if (!productResponse.error && productResponse.data) {
        setProduct(productResponse.data as Product)
      }

      const datasetsResponse = await apiClient.listEvaluationDatasets(productId)
      if (!datasetsResponse.error && datasetsResponse.data) {
        const datasetsList = datasetsResponse.data as EvaluationDataset[]
        setDatasets(datasetsList)
        if (datasetsList.length > 0 && !selectedDataset) {
          setSelectedDataset(datasetsList[0].id)
        }
      }

      const runsResponse = await apiClient.listEvaluationRuns(productId)
      if (!runsResponse.error && runsResponse.data) {
        setRuns(runsResponse.data as EvaluationRun[])
      }
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [productId, selectedDataset])

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/')
      return
    }

    if (status === 'authenticated' && productId) {
      loadData()
    }
  }, [status, router, productId, loadData])

  // Update runsRef when runs change
  useEffect(() => {
    runsRef.current = runs
  }, [runs])

  // Update current time every second ONLY for running evaluations
  useEffect(() => {
    // Only update time for runs that are actually running and have started_at
    const hasRunningRuns = runs.some(
      (run) => (run.status === 'running' || run.status === 'queued' || run.status === 'pending')
        && run.started_at  // Only update if started_at exists
        && run.dag_run_id  // Only update if DAG was triggered
    )

    if (hasRunningRuns) {
      // Update every second for real-time duration
      durationIntervalRef.current = setInterval(() => {
        setCurrentTime(new Date())
      }, 1000)
    } else {
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current)
        durationIntervalRef.current = null
      }
    }

    return () => {
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current)
        durationIntervalRef.current = null
      }
    }
  }, [runs])

  // Check if we need to start polling when runs change
  useEffect(() => {
    // Only poll for runs that:
    // 1. Are in running/queued/pending status
    // 2. Have a dag_run_id (meaning they were successfully triggered)
    const hasRunningRuns = runs.some(
      (run) => (run.status === 'running' || run.status === 'queued' || run.status === 'pending') 
        && run.dag_run_id  // Only poll if DAG was actually triggered
    )

    // Only start polling if:
    // 1. There are running runs with DAG run IDs
    // 2. We're not already polling (interval doesn't exist)
    if (hasRunningRuns && !intervalRef.current) {
      setPolling(true)
      intervalRef.current = setInterval(() => {
        loadData(false).then(() => {
          // Check the latest state from ref after loading
          const stillHasRunning = runsRef.current.some(
            (run) => (run.status === 'running' || run.status === 'queued' || run.status === 'pending')
              && run.dag_run_id
          )
          
          if (!stillHasRunning) {
            // Stop polling if no running runs
            if (intervalRef.current) {
              clearInterval(intervalRef.current)
              intervalRef.current = null
            }
            setPolling(false)
          }
        })
      }, 10000) // Poll every 10 seconds when evaluations are running
    } else if (!hasRunningRuns && intervalRef.current) {
      // Stop polling if no running runs
      clearInterval(intervalRef.current)
      intervalRef.current = null
      setPolling(false)
    }
  }, [runs, loadData])

  // Poll for running evaluations - cleanup effect
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [])

  const handleRunEvaluation = () => {
    if (!selectedDataset) {
      setResultModalData({
        type: 'error',
        title: 'No Dataset Selected',
        message: 'Please select a dataset to run evaluation'
      })
      setShowResultModal(true)
      return
    }

    // Show confirmation modal first
    setShowConfirmModal(true)
  }

  const confirmRunEvaluation = async () => {
    setShowConfirmModal(false)
    
    if (!selectedDataset) {
      return
    }

    setRunning(true)
    try {
      const response = await apiClient.createEvaluationRun(productId, {
        dataset_id: selectedDataset
      })

      if (response.error) {
        // Check for specific error messages and provide user-friendly responses
        let errorTitle = 'Evaluation Failed'
        let errorMessage = response.error
        let actionButton: { label: string; onClick: () => void; variant?: 'primary' | 'secondary' } | undefined = undefined
        
        // Check if error indicates no pipeline run
        if (response.error.includes('No data available') || 
            response.error.includes('run a pipeline first') ||
            response.error.includes('pipeline')) {
          errorTitle = 'Pipeline Required'
          errorMessage = 'No data available for evaluation. Please run a pipeline first to process your data before running evaluations.'
          actionButton = {
            label: 'Run Pipeline',
            onClick: () => {
              setShowResultModal(false)
              router.push(`/app/products/${productId}/pipeline-runs`)
            },
            variant: 'primary' as const
          }
        } else if (response.error.includes('Dataset does not belong')) {
          errorTitle = 'Invalid Dataset'
          errorMessage = 'The selected dataset does not belong to this product. Please select a different dataset.'
        }
        
        setResultModalData({
          type: 'error',
          title: errorTitle,
          message: errorMessage,
          actionButton
        })
        setShowResultModal(true)
      } else {
        // Success - immediately reload data to show the new run
        await loadData(true)
        
        setResultModalData({
          type: 'success',
          title: 'Evaluation Started',
          message: 'Evaluation run has been queued and will start shortly. You can monitor its progress below.'
        })
        setShowResultModal(true)
      }
    } catch (err) {
      setResultModalData({
        type: 'error',
        title: 'Evaluation Failed',
        message: err instanceof Error ? err.message : 'An unexpected error occurred'
      })
      setShowResultModal(true)
    } finally {
      setRunning(false)
    }
  }

  const handleDownloadReport = async (runId: string) => {
    setDownloadingReport(runId)
    try {
      const blob = await apiClient.downloadEvaluationReport(runId)
      
      if (!blob) {
        throw new Error('Failed to download report')
      }

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `evaluation-report-${runId}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Failed to download report:', err)
      setResultModalData({
        type: 'error',
        title: 'Download Failed',
        message: 'Failed to download the evaluation report. Please try again later.'
      })
      setShowResultModal(true)
    } finally {
      setDownloadingReport(null)
    }
  }

  // Memoized duration component
  const DurationCell = React.memo(({ run, currentTime }: { run: EvaluationRun, currentTime: Date }) => {
    const duration = useMemo(() => {
      // If no started_at, return N/A
      if (!run.started_at) return 'N/A'
      
      const start = new Date(run.started_at)
      
      // For completed/failed runs, use finished_at (don't update)
      if (run.status === 'completed' || run.status === 'failed') {
        if (run.finished_at) {
          const end = new Date(run.finished_at)
          const diff = end.getTime() - start.getTime()
          
          const seconds = Math.floor(diff / 1000)
          const minutes = Math.floor(seconds / 60)
          const hours = Math.floor(minutes / 60)
          
          if (hours > 0) {
            return `${hours}h ${minutes % 60}m`
          } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`
          } else {
            return `${seconds}s`
          }
        }
        return 'N/A'
      }
      
      // For running/queued/pending runs, use currentTime for real-time updates
      const end = currentTime
      const diff = end.getTime() - start.getTime()
      
      const seconds = Math.floor(diff / 1000)
      const minutes = Math.floor(seconds / 60)
      const hours = Math.floor(minutes / 60)
      
      if (hours > 0) {
        return `${hours}h ${minutes % 60}m`
      } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`
      } else {
        return `${seconds}s`
      }
    }, [run.started_at, run.finished_at, run.status, currentTime])
    
    return <div className="text-sm text-gray-500">{duration}</div>
  })
  
  DurationCell.displayName = 'DurationCell'

  if (loading) {
    return (
      <AppLayout>
        <div className="p-6">
          <CardSkeleton />
        </div>
      </AppLayout>
    )
  }

  if (!product) {
    return (
      <AppLayout>
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">Product not found</p>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center mb-6">
          <Link href={`/app/products/${productId}/rag-quality`} className="flex items-center text-sm text-gray-600 hover:text-gray-900 transition-colors">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Retrieval Evaluation
          </Link>
          <span className="mx-2 text-gray-400">/</span>
          <span className="text-sm font-medium text-gray-900">Evaluations</span>
        </div>

        {/* Page Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Evaluation Runs</h1>
            <p className="mt-2 text-sm text-gray-600">
              Run evaluations on your datasets and view detailed results.
            </p>
            {product && product.current_version <= 0 && (
              <div className="mt-3 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3 flex-1">
                    <p className="text-sm text-yellow-800">
                      <strong>No pipeline run yet.</strong> You need to run a pipeline first to process your data before running evaluations.
                    </p>
                    <Link href={`/app/products/${productId}/pipeline-runs`} className="mt-2 inline-block">
                      <Button size="sm" className="bg-yellow-600 hover:bg-yellow-700 text-white">
                        Go to Pipeline Runs
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </div>
          {datasets.length > 0 && (
            <div className="flex items-center gap-3">
              <select
                value={selectedDataset}
                onChange={(e) => setSelectedDataset(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              >
                <option value="">Select dataset...</option>
                {datasets.map((dataset) => (
                  <option key={dataset.id} value={dataset.id}>
                    {dataset.name}
                  </option>
                ))}
              </select>
              <Button
                onClick={handleRunEvaluation}
                disabled={running || !selectedDataset || (product && product.current_version <= 0)}
                className="flex items-center gap-2"
              >
                <Play className="h-4 w-4" />
                {running ? 'Triggering...' : 'Run Evaluation'}
              </Button>
            </div>
          )}
        </div>

        {/* Polling indicator */}
        {polling && (
          <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center gap-2">
            <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
            <span className="text-sm text-blue-800">Auto-refreshing evaluation status...</span>
          </div>
        )}

        {/* Runs List */}
        {runs.length > 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Version
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Started
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Duration
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {runs.map((run) => {
                    const isRunning = run.status === 'running' || run.status === 'queued' || run.status === 'pending'
                    
                    return (
                      <tr key={run.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">v{run.version}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <StatusBadge status={mapEvaluationStatus(run.status)} size="sm" />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {run.started_at
                              ? new Date(run.started_at).toLocaleString()
                              : 'Not started'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <DurationCell run={run} currentTime={currentTime} />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-1">
                            {isRunning ? (
                              <div className="flex items-center gap-2 text-sm text-blue-600">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                <span>Running</span>
                              </div>
                            ) : (
                              <>
                                <Link href={`/app/products/${productId}/rag-quality/evaluations/${run.id}`}>
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-8 w-8 p-0"
                                    title="View Details"
                                  >
                                    <Eye className="h-4 w-4" />
                                  </Button>
                                </Link>
                                {run.status === 'completed' && (
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    onClick={() => handleDownloadReport(run.id)}
                                    disabled={downloadingReport === run.id}
                                    className="h-8 w-8 p-0"
                                    title="Download Report"
                                  >
                                    {downloadingReport === run.id ? (
                                      <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                      <Download className="h-4 w-4" />
                                    )}
                                  </Button>
                                )}
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No evaluation runs yet</h3>
            <p className="text-gray-600 mb-6">
              {datasets.length === 0 
                ? 'Create a dataset first, then run your first evaluation.'
                : 'Run an evaluation to see results here.'}
            </p>
            {datasets.length === 0 ? (
              <Link href={`/app/products/${productId}/rag-quality/datasets`}>
                <Button className="flex items-center gap-2">
                  Create Dataset
                </Button>
              </Link>
            ) : (
              <Button
                onClick={handleRunEvaluation}
                disabled={!selectedDataset || (product && product.current_version <= 0)}
                className="flex items-center gap-2"
              >
                <Play className="h-4 w-4" />
                Run Evaluation
              </Button>
            )}
          </div>
        )}

        {showResultModal && resultModalData && (
          <ResultModal
            type={resultModalData.type}
            title={resultModalData.title}
            message={resultModalData.message}
            onClose={() => setShowResultModal(false)}
            actionButton={resultModalData.actionButton}
          />
        )}

        <ConfirmModal
          isOpen={showConfirmModal}
          onClose={() => setShowConfirmModal(false)}
          onConfirm={confirmRunEvaluation}
          title="Run Evaluation"
          message="Are you sure you want to run an evaluation on the selected dataset? This will evaluate your retrieval system's performance metrics including groundedness, context relevance, answer relevance, and citation coverage."
          confirmText="Run Evaluation"
          cancelText="Cancel"
          variant="info"
        />
      </div>
    </AppLayout>
  )
}
