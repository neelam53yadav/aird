'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Play, RefreshCw, Clock, CheckCircle, XCircle, AlertTriangle, Loader2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient, PipelineRun } from '@/lib/api-client'
import { useToast } from '@/components/ui/toast'

export default function PipelineRunsPage() {
  const params = useParams()
  const router = useRouter()
  const productId = params.id as string
  const { addToast } = useToast()

  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)
  const [triggering, setTriggering] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [pipelineConflict, setPipelineConflict] = useState<any>(null)

  const loadPipelineRuns = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true)
    setError(null)
    
    try {
      const response = await apiClient.getPipelineRuns(productId, 50)
      
      if (response.error) {
        setError(response.error)
        addToast({
          type: 'error',
          message: `Failed to load pipeline runs: ${response.error}`,
        })
      } else if (response.data) {
        setPipelineRuns(response.data)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load pipeline runs'
      setError(errorMessage)
      addToast({
        type: 'error',
        message: errorMessage,
      })
    } finally {
      setLoading(false)
    }
  }, [productId, addToast])

  useEffect(() => {
    loadPipelineRuns()
  }, [loadPipelineRuns])

  // Poll for running pipelines
  useEffect(() => {
    const hasRunningRuns = pipelineRuns.some(
      (run) => run.status === 'running' || run.status === 'queued'
    )

    if (hasRunningRuns && !polling) {
      setPolling(true)
      const interval = setInterval(() => {
        loadPipelineRuns(false) // Don't show loading spinner during polling
      }, 5000) // Poll every 5 seconds

      return () => {
        clearInterval(interval)
        setPolling(false)
      }
    } else if (!hasRunningRuns) {
      setPolling(false)
    }
  }, [pipelineRuns, polling, loadPipelineRuns])

  const handleTriggerPipeline = async (forceRun: boolean = false) => {
    setTriggering(true)
    setPipelineConflict(null)
    try {
      const response = await apiClient.triggerPipeline(productId, undefined, forceRun)
      
      if (response.error) {
        // Check if it's a conflict error (409)
        if (response.status === 409) {
          // Handle both structured errorData and plain error messages
          const conflictData = response.errorData && typeof response.errorData === 'object' 
            ? response.errorData 
            : { message: response.error || 'A pipeline run is already in progress' }
          setPipelineConflict(conflictData)
          return
        }
        
        addToast({
          type: 'error',
          message: typeof response.error === 'string' ? response.error : 'Failed to trigger pipeline',
        })
      } else if (response.data) {
        addToast({
          type: 'success',
          message: `Pipeline run triggered successfully. Version: ${response.data.version}`,
        })
        // Refresh runs after a short delay
        setTimeout(() => {
          loadPipelineRuns()
        }, 1000)
      }
    } catch (err) {
      addToast({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to trigger pipeline',
      })
    } finally {
      setTriggering(false)
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    try {
      const response = await apiClient.syncPipelineRuns()
      
      if (response.error) {
        addToast({
          type: 'error',
          message: `Failed to sync: ${response.error}`,
        })
      } else if (response.data) {
        addToast({
          type: 'success',
          message: `Synced ${response.data.updated_count} pipeline runs`,
        })
        loadPipelineRuns()
      }
    } catch (err) {
      addToast({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to sync',
      })
    } finally {
      setSyncing(false)
    }
  }

  const getStatusIcon = (status: PipelineRun['status']) => {
    switch (status) {
      case 'queued':
        return <Clock className="h-4 w-4 text-gray-500" />
      case 'running':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      case 'succeeded':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'ready_with_warnings':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case 'failed_policy':
        return <XCircle className="h-4 w-4 text-orange-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusColor = (status: PipelineRun['status']) => {
    switch (status) {
      case 'queued':
        return 'bg-gray-100 text-gray-800'
      case 'running':
        return 'bg-blue-100 text-blue-800'
      case 'succeeded':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'ready_with_warnings':
        return 'bg-yellow-100 text-yellow-800'
      case 'failed_policy':
        return 'bg-orange-100 text-orange-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatDuration = (startedAt?: string, finishedAt?: string) => {
    if (!startedAt) return 'N/A'
    
    const start = new Date(startedAt)
    const end = finishedAt ? new Date(finishedAt) : new Date()
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

  const getAirdStagesInfo = (metrics: PipelineRun['metrics']) => {
    const stages = metrics?.aird_stages || {}
    const completed = metrics?.aird_stages_completed || []
    
    if (Object.keys(stages).length === 0 && completed.length === 0) {
      return null
    }
    
    return {
      total: Object.keys(stages).length,
      completed: completed.length,
      stages: Object.keys(stages),
    }
  }

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link
            href={`/app/products/${productId}`}
            className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Product
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Pipeline Runs</h1>
              <p className="mt-2 text-sm text-gray-600">
                Monitor and manage data pipeline execution runs
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={handleSync}
                disabled={syncing}
                className="flex items-center gap-2"
              >
                <RefreshCw className={`h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
                {syncing ? 'Syncing...' : 'Sync with Airflow'}
              </Button>
              <Button
                onClick={() => handleTriggerPipeline(false)}
                disabled={triggering}
                className="flex items-center gap-2"
              >
                <Play className="h-4 w-4" />
                {triggering ? 'Triggering...' : 'Trigger Pipeline'}
              </Button>
            </div>
          </div>
        </div>

        {/* Pipeline Conflict Modal */}
        {pipelineConflict && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
              <div className="flex items-center mb-4">
                <AlertTriangle className="h-6 w-6 text-orange-600 mr-3" />
                <h3 className="text-lg font-semibold text-gray-900">Pipeline Already Running</h3>
              </div>
              <div className="mb-6">
                <p className="text-sm text-gray-700 mb-2">
                  {pipelineConflict.message || 'A pipeline run is already in progress for this product and version.'}
                </p>
                {pipelineConflict.existing_status && (
                  <p className="text-sm text-gray-600">
                    Current status: <strong>{pipelineConflict.existing_status}</strong>
                  </p>
                )}
                <p className="text-sm text-gray-600 mt-3">
                  {pipelineConflict.suggestion || 'You can force run to cancel the existing run and start a new one, or wait for the current run to complete.'}
                </p>
              </div>
              <div className="flex justify-end space-x-3">
                <Button
                  variant="outline"
                  onClick={() => setPipelineConflict(null)}
                  disabled={triggering}
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => handleTriggerPipeline(true)}
                  disabled={triggering}
                  className="bg-orange-600 hover:bg-orange-700 text-white"
                >
                  {triggering ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Starting...
                    </>
                  ) : (
                    'Force Run (Override)'
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <XCircle className="h-5 w-5 text-red-600 mr-2" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && pipelineRuns.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <Loader2 className="h-8 w-8 text-gray-400 animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Loading pipeline runs...</p>
          </div>
        ) : pipelineRuns.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No pipeline runs yet</h3>
            <p className="text-gray-600 mb-6">
              Trigger a pipeline run to start processing your data product.
            </p>
            <Button onClick={() => handleTriggerPipeline(false)} disabled={triggering}>
              <Play className="h-4 w-4 mr-2" />
              {triggering ? 'Triggering...' : 'Trigger First Pipeline Run'}
            </Button>
          </div>
        ) : (
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
                      AIRD Stages
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      DAG Run ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {pipelineRuns.map((run) => {
                    const stagesInfo = getAirdStagesInfo(run.metrics)
                    return (
                      <tr key={run.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">v{run.version}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(run.status)}
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(run.status)}`}>
                              {run.status.replace('_', ' ')}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {run.started_at
                              ? new Date(run.started_at).toLocaleString()
                              : 'Not started'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {formatDuration(run.started_at, run.finished_at)}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          {stagesInfo ? (
                            <div className="text-sm text-gray-900">
                              <div className="font-medium">
                                {stagesInfo.completed}/{stagesInfo.total} completed
                              </div>
                              {stagesInfo.stages.length > 0 && (
                                <div className="text-xs text-gray-500 mt-1">
                                  {stagesInfo.stages.slice(0, 3).join(', ')}
                                  {stagesInfo.stages.length > 3 && '...'}
                                </div>
                              )}
                            </div>
                          ) : (
                            <span className="text-sm text-gray-400">No stages tracked</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500 font-mono">
                            {run.dag_run_id ? (
                              <span className="truncate max-w-xs inline-block" title={run.dag_run_id}>
                                {run.dag_run_id}
                              </span>
                            ) : (
                              <span className="text-gray-400">N/A</span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {(run.status === 'running' || run.status === 'queued') && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleCancelRun(run.id)}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            >
                              <X className="h-4 w-4 mr-1" />
                              Cancel
                            </Button>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Polling Indicator */}
        {polling && (
          <div className="mt-4 text-center">
            <p className="text-sm text-gray-500 flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Auto-refreshing pipeline status...
            </p>
          </div>
        )}
      </div>
    </AppLayout>
  )
}




