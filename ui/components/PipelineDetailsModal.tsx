'use client'

import { useState, useEffect } from 'react'
import { X, CheckCircle, XCircle, Clock, Loader2, ChevronDown, ChevronUp, FileText, Square } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useToast } from '@/components/ui/toast'

// Pipeline task execution order (matches Airflow DAG dependencies)
const PIPELINE_TASK_ORDER = [
  'preprocess',
  'scoring',
  'fingerprint',
  'validation',
  'policy',
  'reporting',
  'indexing',
  'validate_data_quality',
  'finalize',
]

interface PipelineDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  runId: string
  runVersion: number
  runStatus: string
  initialMetrics?: any
  onPipelineCancelled?: () => void
}

export default function PipelineDetailsModal({
  isOpen,
  onClose,
  runId,
  runVersion,
  runStatus,
  initialMetrics,
  onPipelineCancelled,
}: PipelineDetailsModalProps) {
  const [logs, setLogs] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set())
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set())
  const { addToast } = useToast()

  useEffect(() => {
    if (isOpen && runId) {
      loadLogs()
    }
  }, [isOpen, runId])

  const loadLogs = async () => {
    setLoading(true)
    try {
      const response = await apiClient.getPipelineRunLogs(runId)
      if (response.error) {
        addToast({
          type: 'error',
          message: `Failed to load logs: ${response.error}`,
        })
      } else {
        setLogs(response.data)
      }
    } catch (err) {
      addToast({
        type: 'error',
        message: 'Failed to load pipeline logs',
      })
    } finally {
      setLoading(false)
    }
  }

  const toggleStage = (stageName: string) => {
    const newExpanded = new Set(expandedStages)
    if (newExpanded.has(stageName)) {
      newExpanded.delete(stageName)
    } else {
      newExpanded.add(stageName)
    }
    setExpandedStages(newExpanded)
  }

  const toggleTask = (taskId: string) => {
    const newExpanded = new Set(expandedTasks)
    if (newExpanded.has(taskId)) {
      newExpanded.delete(taskId)
    } else {
      newExpanded.add(taskId)
    }
    setExpandedTasks(newExpanded)
  }

  const handleCancelPipeline = async () => {
    // Confirm cancellation
    const confirmed = window.confirm(
      `Are you sure you want to stop this pipeline run (Version ${runVersion})? This action cannot be undone.`
    )
    
    if (!confirmed) return

    setCancelling(true)
    try {
      const response = await apiClient.cancelPipelineRun(runId)
      
      if (response.error) {
        addToast({
          type: 'error',
          message: `Failed to stop pipeline: ${response.error}`,
        })
      } else {
        addToast({
          type: 'success',
          message: 'Pipeline stopped successfully',
        })
        
        // Refresh logs to show updated status
        await loadLogs()
        
        // Notify parent to refresh pipeline runs list
        if (onPipelineCancelled) {
          onPipelineCancelled()
        }
      }
    } catch (err) {
      console.error('Failed to cancel pipeline:', err)
      addToast({
        type: 'error',
        message: 'Failed to stop pipeline. Please try again.',
      })
    } finally {
      setCancelling(false)
    }
  }

  // Check if pipeline can be cancelled (more robust status check)
  const canCancel = runStatus && (
    runStatus.toLowerCase() === 'running' || 
    runStatus.toLowerCase() === 'queued'
  )

  const getStageStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'succeeded':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'running':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'success':
      case 'succeeded':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'running':
        return 'bg-blue-100 text-blue-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  // Helper function to sort tasks by execution order
  const sortTasksByOrder = (tasks: [string, any][]): [string, any][] => {
    return tasks.sort(([taskA], [taskB]) => {
      const indexA = PIPELINE_TASK_ORDER.indexOf(taskA)
      const indexB = PIPELINE_TASK_ORDER.indexOf(taskB)
      // If task not in order list, put it at the end
      if (indexA === -1 && indexB === -1) return 0
      if (indexA === -1) return 1
      if (indexB === -1) return -1
      return indexA - indexB
    })
  }

  const stageMetrics = logs?.stage_metrics || initialMetrics?.aird_stages || {}

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={onClose} />

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white">Pipeline Run Details</h3>
              <p className="text-sm text-blue-100 mt-1">Version {runVersion} • {runStatus}</p>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:text-gray-200 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4 max-h-[70vh] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              </div>
            ) : (
              <div className="space-y-4">
                {/* Stage Status Overview */}
                {Object.keys(stageMetrics).length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">Pipeline Stages</h4>
                    <div className="space-y-2">
                      {sortTasksByOrder(Object.entries(stageMetrics)).map(([stageName, stageData]: [string, any]) => (
                        <div
                          key={stageName}
                          className="border border-gray-200 rounded-lg overflow-hidden"
                        >
                          <button
                            onClick={() => toggleStage(stageName)}
                            className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
                          >
                            <div className="flex items-center space-x-3">
                              {getStageStatusIcon(stageData?.status)}
                              <span className="font-medium text-gray-900 capitalize">
                                {stageName.replace(/_/g, ' ')}
                              </span>
                              {stageData?.error && (
                                <span className="text-xs text-red-600">(Error)</span>
                              )}
                            </div>
                            {expandedStages.has(stageName) ? (
                              <ChevronUp className="h-4 w-4 text-gray-500" />
                            ) : (
                              <ChevronDown className="h-4 w-4 text-gray-500" />
                            )}
                          </button>

                          {expandedStages.has(stageName) && (
                            <div className="px-4 py-3 bg-white border-t border-gray-200">
                              {stageData?.error && (
                                <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded">
                                  <p className="text-sm font-medium text-red-800">Error:</p>
                                  <p className="text-sm text-red-700 mt-1">{stageData.error}</p>
                                </div>
                              )}
                              {stageData?.metrics && Object.keys(stageData.metrics).length > 0 && (
                                <div className="text-sm text-gray-600">
                                  <p className="font-medium mb-1">Metrics:</p>
                                  <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                                    {JSON.stringify(stageData.metrics, null, 2)}
                                  </pre>
                                </div>
                              )}
                              {stageData?.started_at && (
                                <p className="text-xs text-gray-500 mt-2">
                                  Started: {new Date(stageData.started_at).toLocaleString()}
                                </p>
                              )}
                              {stageData?.finished_at && (
                                <p className="text-xs text-gray-500">
                                  Finished: {new Date(stageData.finished_at).toLocaleString()}
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Task Logs */}
                {logs?.logs && Object.keys(logs.logs).length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">Task Logs</h4>
                    <div className="space-y-2">
                      {sortTasksByOrder(Object.entries(logs.logs)).map(([taskId, taskLog]: [string, any]) => (
                        <div
                          key={taskId}
                          className="border border-gray-200 rounded-lg overflow-hidden"
                        >
                          <button
                            onClick={() => toggleTask(taskId)}
                            className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
                          >
                            <div className="flex items-center space-x-2">
                              <FileText className="h-4 w-4 text-gray-500" />
                              <span className="font-medium text-gray-900">{taskId}</span>
                              {taskLog.status && (
                                <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(taskLog.status)}`}>
                                  {taskLog.status}
                                </span>
                              )}
                            </div>
                            {expandedTasks.has(taskId) ? (
                              <ChevronUp className="h-4 w-4 text-gray-500" />
                            ) : (
                              <ChevronDown className="h-4 w-4 text-gray-500" />
                            )}
                          </button>

                          {expandedTasks.has(taskId) && (
                            <div className="px-4 py-3 bg-gray-900 text-gray-100 border-t border-gray-200">
                              {taskLog.content ? (
                                <pre className="text-xs font-mono whitespace-pre-wrap overflow-x-auto">
                                  {taskLog.content}
                                </pre>
                              ) : taskLog.error ? (
                                <p className="text-xs text-red-400">{taskLog.error}</p>
                              ) : (
                                <p className="text-xs text-gray-400">No logs available</p>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {logs?.error && (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm text-yellow-800">{logs.error}</p>
                  </div>
                )}

                {Object.keys(stageMetrics).length === 0 && (!logs?.logs || Object.keys(logs.logs).length === 0) && (
                  <div className="text-center py-8 text-gray-500">
                    <p>No stage information or logs available for this pipeline run.</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-3 flex justify-between items-center">
            <div>
              {canCancel && (
                <button
                  onClick={handleCancelPipeline}
                  disabled={cancelling}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-red-700 rounded-md hover:bg-red-700 disabled:bg-red-400 disabled:cursor-not-allowed flex items-center space-x-2 transition-colors"
                >
                  {cancelling ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Stopping...</span>
                    </>
                  ) : (
                    <>
                      <Square className="h-4 w-4" />
                      <span>Stop Pipeline</span>
                    </>
                  )}
                </button>
              )}
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

