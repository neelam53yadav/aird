'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Play, Clock, CheckCircle, XCircle, AlertTriangle, Loader2, X, Eye, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient, PipelineRun } from '@/lib/api-client'
import { useToast } from '@/components/ui/toast'
import PipelineDetailsModal from '@/components/PipelineDetailsModal'
import ChunkingConfigModal from '@/components/ChunkingConfigModal'

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
  const [pipelineConflict, setPipelineConflict] = useState<any>(null)
  const [currentPage, setCurrentPage] = useState(0)
  const [totalRuns, setTotalRuns] = useState(0)
  const [product, setProduct] = useState<any>(null)
  const [promotingVersion, setPromotingVersion] = useState<number | null>(null)
  const [selectedRunForDetails, setSelectedRunForDetails] = useState<PipelineRun | null>(null)
  const [selectedChunkingConfig, setSelectedChunkingConfig] = useState<any | null>(null)
  const RUNS_PER_PAGE = 20
  
  // Ref to track the polling interval
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  // Ref to track latest pipelineRuns state for checking inside interval callback
  const pipelineRunsRef = useRef<PipelineRun[]>([])

  const loadProduct = useCallback(async () => {
    try {
      const response = await apiClient.getProduct(productId)
      if (response.error) {
        console.error('Failed to load product:', response.error)
      } else if (response.data) {
        setProduct(response.data)
      }
    } catch (err) {
      console.error('Failed to load product:', err)
    }
  }, [productId])

  const loadPipelineRuns = useCallback(async (page: number, showLoading = true) => {
    if (showLoading) setLoading(true)
    setError(null)
    
    try {
      const offset = page * RUNS_PER_PAGE
      const response = await apiClient.getPipelineRuns(productId, RUNS_PER_PAGE, offset)
      
      if (response.error) {
        setError(response.error)
        addToast({
          type: 'error',
          message: `Failed to load pipeline runs: ${response.error}`,
        })
      } else if (response.data) {
        // Handle both old format (array) and new format (object with runs, total, etc.)
        if (Array.isArray(response.data)) {
          setPipelineRuns(response.data)
          setTotalRuns(response.data.length)
        } else {
          setPipelineRuns(response.data.runs || [])
          setTotalRuns(response.data.total || 0)
        }
        setCurrentPage(page)
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
    loadProduct()
    loadPipelineRuns(0, true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId]) // Only reload when productId changes

  // Update pipelineRunsRef whenever pipelineRuns changes
  useEffect(() => {
    pipelineRunsRef.current = pipelineRuns
  }, [pipelineRuns])

  // Poll for running pipelines
  useEffect(() => {
    // Clear any existing interval first
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    // Check initial state
    const hasRunningRuns = pipelineRuns.some(
      (run) => run.status === 'running' || run.status === 'queued'
    )

    if (hasRunningRuns) {
      setPolling(true)
      intervalRef.current = setInterval(() => {
        loadPipelineRuns(currentPage, false).then(() => {
          // Check the latest state from ref after loading
          const stillHasRunning = pipelineRunsRef.current.some(
            (run) => run.status === 'running' || run.status === 'queued'
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
      }, 90000) // Poll every 90 seconds
    } else {
      setPolling(false)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      setPolling(false)
    }
    // Only recreate when loadPipelineRuns or currentPage changes
    // This prevents constant recreation when pipelineRuns updates
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadPipelineRuns, currentPage])

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
          loadPipelineRuns(currentPage, false) // Don't show loading spinner during refresh
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

  const handleCancelRun = async (runId: string) => {
    try {
      const response = await apiClient.cancelPipelineRun(runId)
      if (response.error) {
        addToast({
          type: 'error',
          message: `Failed to cancel run: ${response.error}`,
        })
      } else {
        addToast({
          type: 'success',
          message: 'Pipeline run cancelled successfully',
        })
        loadPipelineRuns(currentPage, false)
      }
    } catch (err) {
      addToast({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to cancel run',
      })
    }
  }

  const handlePromoteVersion = async (version: number) => {
    if (!product) return
    
    setPromotingVersion(version)
    try {
      const response = await apiClient.promoteVersion(product.id, version)
      
      if (response.error) {
        addToast({
          type: 'error',
          message: typeof response.error === 'string' ? response.error : 'Failed to promote version',
        })
      } else {
        addToast({
          type: 'success',
          message: `Version ${version} has been promoted to production successfully`,
        })
        
        // Refresh product data to get updated promoted_version
        await loadProduct()
      }
    } catch (err) {
      addToast({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to promote version',
      })
    } finally {
      setPromotingVersion(null)
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

  const getChunkingConfigForRun = (run: PipelineRun) => {
    // For successful runs, check if product has chunking_config with resolved_settings
    if (run.status === 'succeeded' && product?.chunking_config?.resolved_settings) {
      return product.chunking_config.resolved_settings
    }
    return null
  }

  const formatChunkingConfigSummary = (config: any) => {
    if (!config) return null
    const parts = []
    if (config.chunk_size) parts.push(`Size: ${config.chunk_size}`)
    if (config.chunk_overlap !== undefined) parts.push(`Overlap: ${config.chunk_overlap}`)
    if (config.chunking_strategy) parts.push(`Strategy: ${config.chunking_strategy.replace(/_/g, ' ')}`)
    if (config.content_type) parts.push(`Type: ${config.content_type}`)
    return parts.length > 0 ? parts.join(', ') : 'Available'
  }

  const handleViewDetails = (run: PipelineRun) => {
    setSelectedRunForDetails(run)
  }

  const handleCloseDetails = () => {
    setSelectedRunForDetails(null)
  }

  const handlePipelineCancelled = () => {
    loadPipelineRuns(currentPage, false)
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
                      Chunking Config
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {pipelineRuns.map((run) => {
                    const stagesInfo = getAirdStagesInfo(run.metrics)
                    const chunkingConfig = getChunkingConfigForRun(run)
                    const configSummary = formatChunkingConfigSummary(chunkingConfig)
                    return (
                      <tr key={run.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center space-x-2">
                            <span className="text-sm font-medium text-gray-900">v{run.version}</span>
                            {product?.promoted_version === run.version && (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-sm">
                                🚀 PROD
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(run.status || 'unknown')}
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(run.status || 'unknown')}`}>
                              {(run.status || 'unknown').replace(/_/g, ' ')}
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
                            <div className="text-sm text-gray-900 mb-2">
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
                          ) : null}
                          <div>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleViewDetails(run)}
                              className="flex items-center gap-1"
                            >
                              <Eye className="h-4 w-4" />
                              View Stages
                            </Button>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          {chunkingConfig ? (
                            <button
                              onClick={() => setSelectedChunkingConfig(chunkingConfig)}
                              className="text-sm text-blue-600 hover:text-blue-800 hover:underline cursor-pointer text-left"
                            >
                              {configSummary || 'View Config'}
                            </button>
                          ) : (
                            <span className="text-sm text-gray-400">No config</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            {(run.status === 'running' || run.status === 'queued') && run.id && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleCancelRun(run.id!)}
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              >
                                <Square className="h-4 w-4 mr-1" />
                                Stop
                              </Button>
                            )}
                            {run.status === 'succeeded' && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handlePromoteVersion(run.version)}
                                disabled={promotingVersion === run.version || product?.promoted_version === run.version}
                                className={
                                  product?.promoted_version === run.version
                                    ? 'bg-green-100 text-green-800 hover:bg-green-100 cursor-default'
                                    : promotingVersion === run.version
                                    ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                                    : 'bg-blue-100 text-blue-800 hover:bg-blue-200'
                                }
                              >
                                {product?.promoted_version === run.version
                                  ? '✓ Promoted'
                                  : promotingVersion === run.version
                                  ? 'Promoting...'
                                  : 'Promote to Prod'}
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {/* Pagination Controls */}
            {totalRuns > RUNS_PER_PAGE && (
              <div className="mt-4 flex items-center justify-between border-t border-gray-200 px-6 py-4 bg-white">
                <div className="text-sm text-gray-700">
                  Showing {currentPage * RUNS_PER_PAGE + 1} to{' '}
                  {Math.min((currentPage + 1) * RUNS_PER_PAGE, totalRuns)} of{' '}
                  {totalRuns} runs
                </div>
                <div className="flex space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => loadPipelineRuns(currentPage - 1)}
                    disabled={currentPage === 0 || loading}
                    className="px-3 py-1.5"
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => loadPipelineRuns(currentPage + 1)}
                    disabled={(currentPage + 1) * RUNS_PER_PAGE >= totalRuns || loading}
                    className="px-3 py-1.5"
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
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

        {/* Pipeline Details Modal */}
        {selectedRunForDetails && (
          <PipelineDetailsModal
            isOpen={!!selectedRunForDetails}
            onClose={handleCloseDetails}
            runId={selectedRunForDetails.id!}
            runVersion={selectedRunForDetails.version}
            runStatus={selectedRunForDetails.status || 'unknown'}
            initialMetrics={selectedRunForDetails.metrics}
            onPipelineCancelled={handlePipelineCancelled}
          />
        )}

        {/* Chunking Config Modal */}
        <ChunkingConfigModal
          isOpen={!!selectedChunkingConfig}
          onClose={() => setSelectedChunkingConfig(null)}
          config={selectedChunkingConfig}
        />
      </div>
    </AppLayout>
  )
}




