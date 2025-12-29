'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { ArrowLeft, TrendingUp, Clock, Database, Zap, BarChart3, ExternalLink } from 'lucide-react'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient } from '@/lib/api-client'
import { formatEmbeddingModelName } from '@/lib/embedding-models'

interface Product {
  id: string
  workspace_id: string
  owner_user_id: string
  name: string
  status: 'draft' | 'running' | 'ready' | 'failed'
  current_version: number
  promoted_version?: number
  created_at: string
  updated_at?: string
}

interface PipelineRun {
  id: string
  product_id: string
  version: number
  status: 'succeeded' | 'failed' | 'running' | 'queued'
  started_at: string
  finished_at?: string
  dag_run_id?: string
  metrics: any
  created_at: string
}

interface MLflowMetrics {
  has_mlflow_data: boolean
  experiment_id?: string
  experiment_name?: string
  version?: number
  latest_run?: {
    run_id: string
    start_time: string
    end_time: string
    status: string
    status_note?: string
    chunk_count: number
    avg_chunk_size: number
    embedding_count: number
    vector_count: number
    processing_time_seconds: number
    chunk_size: string
    chunk_overlap: string
    embedder_name: string
    embedding_dimension: string
  }
  run_summary?: {
    total_runs: number
    successful_runs: number
    failed_runs: number
    has_mixed_status: boolean
  }
  mlflow_ui_url?: string
  message?: string
}

export default function PipelineMetricsPage() {
  const params = useParams()
  const router = useRouter()
  const productId = params.id as string

  const [product, setProduct] = useState<Product | null>(null)
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([])
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null)
  const [versionMetrics, setVersionMetrics] = useState<MLflowMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMetrics, setLoadingMetrics] = useState(false)

  useEffect(() => {
    loadProduct()
    loadPipelineRuns()
  }, [productId])

  const loadProduct = async () => {
    try {
      const response = await apiClient.getProduct(productId)
      if (response.error) {
        console.error('Failed to load product:', response.error)
        return
      }
      setProduct(response.data as Product)
    } catch (err) {
      console.error('Error loading product:', err)
    }
  }

  const loadPipelineRuns = async () => {
    try {
      const response = await apiClient.getPipelineRuns(productId, 20)
      if (response.error) {
        console.error('Failed to load pipeline runs:', response.error)
        return
      }
      setPipelineRuns(response.data as PipelineRun[])
    } catch (err) {
      console.error('Error loading pipeline runs:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadVersionMetrics = async (version: number) => {
    setLoadingMetrics(true)
    setSelectedVersion(version)
    try {
      const response = await apiClient.getMLflowMetricsForVersion(productId, version)
      if (response.error) {
        console.error('Failed to load version metrics:', response.error)
        setVersionMetrics({
          has_mlflow_data: false,
          message: response.error
        })
        return
      }
      setVersionMetrics(response.data as MLflowMetrics)
    } catch (err) {
      console.error('Error loading version metrics:', err)
      setVersionMetrics({
        has_mlflow_data: false,
        message: 'Failed to load metrics'
      })
    } finally {
      setLoadingMetrics(false)
    }
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60)
      const remainingSeconds = seconds % 60
      return `${minutes}m ${remainingSeconds.toFixed(0)}s`
    } else {
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      return `${hours}h ${minutes}m`
    }
  }

  const formatEmbeddingModel = (modelName: string) => {
    if (!modelName || modelName === 'N/A') return 'N/A'
    return formatEmbeddingModelName(modelName)
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'succeeded':
      case 'finished':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'partial_success':
        return 'bg-orange-100 text-orange-800'
      case 'running':
        return 'bg-blue-100 text-blue-800'
      case 'queued':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <AppLayout>
        <div className="p-6 flex items-center justify-center min-h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading pipeline metrics...</p>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="p-6 bg-gradient-to-br from-gray-50 via-blue-50/30 to-indigo-50/30 min-h-screen">
        <div className="max-w-7xl mx-auto">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center mb-6">
          <Link href="/app/products" className="flex items-center text-sm text-gray-500 hover:text-gray-700 transition-colors">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Products
          </Link>
          <span className="mx-2 text-gray-400">/</span>
          <Link href={`/app/products/${productId}`} className="text-sm text-gray-500 hover:text-gray-700 transition-colors">
            {product?.name}
          </Link>
          <span className="mx-2 text-gray-400">/</span>
          <span className="text-sm text-gray-900 font-medium">Pipeline Metrics</span>
        </div>

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-3 mr-4 shadow-lg">
                <BarChart3 className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Pipeline Metrics</h1>
                <p className="text-gray-600 mt-1">
                  Detailed metrics for each pipeline version of {product?.name}
                </p>
              </div>
            </div>
            {product?.promoted_version && (
              <div className="inline-flex items-center px-4 py-2 rounded-full text-sm font-bold bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-md">
                🚀 Production Version: v{product.promoted_version}
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Pipeline Runs List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-lg border-2 border-gray-100 p-6">
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                  <BarChart3 className="h-5 w-5" />
                  <span>Pipeline Versions</span>
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Select a version to view detailed metrics
                </p>
              </div>
              <div>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {pipelineRuns.map((run) => (
                    <div
                      key={run.id}
                      className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                        selectedVersion === run.version
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => loadVersionMetrics(run.version)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium">v{run.version}</span>
                          {product?.promoted_version === run.version && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                              🚀 PROD
                            </span>
                          )}
                        </div>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(run.status)}`}>
                          {run.status}
                        </span>
                      </div>
                      <div className="text-sm text-gray-600">
                        <div>Started: {new Date(run.started_at).toLocaleString()}</div>
                        {run.finished_at && (
                          <div>Finished: {new Date(run.finished_at).toLocaleString()}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Metrics Display */}
          <div className="lg:col-span-2">
            {!selectedVersion ? (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      Select a Version
                    </h3>
                    <p className="text-gray-600">
                      Choose a pipeline version from the list to view detailed metrics
                    </p>
                  </div>
                </div>
              </div>
            ) : loadingMetrics ? (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              </div>
            ) : versionMetrics && versionMetrics.has_mlflow_data ? (
              <div className="space-y-6">
                {/* Header */}
                <div className="bg-white rounded-xl shadow-lg border-2 border-gray-100 p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                        <TrendingUp className="h-5 w-5" />
                        <span>Version {selectedVersion} Metrics</span>
                        {product?.promoted_version === selectedVersion && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                            🚀 PRODUCTION
                          </span>
                        )}
                      </h2>
                      <p className="text-sm text-gray-600 mt-1">
                        Detailed performance metrics for pipeline version {selectedVersion}
                      </p>
                    </div>
                    {versionMetrics.mlflow_ui_url && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => window.open(versionMetrics.mlflow_ui_url, '_blank')}
                        className="flex items-center space-x-2"
                      >
                        <ExternalLink className="h-4 w-4" />
                        <span>View in MLflow</span>
                      </Button>
                    )}
                  </div>
                </div>

                {/* Key Metrics */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="bg-white rounded-xl shadow-md border border-gray-100 p-6 hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
                    <div className="flex items-center">
                      <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-3 mr-4 shadow-sm">
                        <Database className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-600 mb-1">Chunks</p>
                        <p className="text-3xl font-bold text-gray-900">
                          {versionMetrics.latest_run?.chunk_count || 0}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white rounded-xl shadow-md border border-gray-100 p-6 hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
                    <div className="flex items-center">
                      <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl p-3 mr-4 shadow-sm">
                        <Zap className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-600 mb-1">Vectors</p>
                        <p className="text-3xl font-bold text-gray-900">
                          {versionMetrics.latest_run?.vector_count || 0}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white rounded-xl shadow-md border border-gray-100 p-6 hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
                    <div className="flex items-center">
                      <div className="bg-gradient-to-br from-orange-500 to-red-600 rounded-xl p-3 mr-4 shadow-sm">
                        <Clock className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-600 mb-1">Processing Time</p>
                        <p className="text-3xl font-bold text-gray-900">
                          {formatDuration(versionMetrics.latest_run?.processing_time_seconds || 0)}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white rounded-xl shadow-md border border-gray-100 p-6 hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
                    <div className="flex items-center">
                      <div className="bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl p-3 mr-4 shadow-sm">
                        <BarChart3 className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-600 mb-1">Avg Chunk Size</p>
                        <p className="text-3xl font-bold text-gray-900">
                          {Math.round(versionMetrics.latest_run?.avg_chunk_size || 0)}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Configuration Details */}
                <div className="bg-white rounded-xl shadow-lg border-2 border-gray-100 p-6">
                  <div className="mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">Configuration</h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Chunk Size</p>
                      <p className="text-lg font-semibold text-gray-900">
                        {versionMetrics.latest_run?.chunk_size || 'N/A'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600">Chunk Overlap</p>
                      <p className="text-lg font-semibold text-gray-900">
                        {versionMetrics.latest_run?.chunk_overlap || 'N/A'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600">Embedder</p>
                      <p className="text-lg font-semibold text-gray-900">
                        {formatEmbeddingModel(versionMetrics.latest_run?.embedder_name || 'N/A')}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600">Embedding Dimension</p>
                      <p className="text-lg font-semibold text-gray-900">
                        {versionMetrics.latest_run?.embedding_dimension || 'N/A'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Run Details */}
                <div className="bg-white rounded-xl shadow-lg border-2 border-gray-100 p-6">
                  <div className="mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">Run Details</h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-medium text-gray-600">Run ID</p>
                      <p className="text-sm font-mono text-gray-900">
                        {versionMetrics.latest_run?.run_id || 'N/A'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600">Status</p>
                      <div className="space-y-2">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(versionMetrics.latest_run?.status || 'unknown')}`}>
                          {versionMetrics.latest_run?.status || 'N/A'}
                        </span>
                        {versionMetrics.latest_run?.status_note && (
                          <p className="text-xs text-orange-600 italic">
                            {versionMetrics.latest_run.status_note}
                          </p>
                        )}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600">Start Time</p>
                      <p className="text-sm text-gray-900">
                        {versionMetrics.latest_run?.start_time 
                          ? new Date(versionMetrics.latest_run.start_time).toLocaleString()
                          : 'N/A'
                        }
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600">End Time</p>
                      <p className="text-sm text-gray-900">
                        {versionMetrics.latest_run?.end_time 
                          ? new Date(versionMetrics.latest_run.end_time).toLocaleString()
                          : 'N/A'
                        }
                      </p>
                    </div>
                  </div>
                </div>

                {/* Run Summary - Show when there are multiple runs or mixed status */}
                {versionMetrics.run_summary && (versionMetrics.run_summary.total_runs > 1 || versionMetrics.run_summary.has_mixed_status) && (
                  <div className="bg-white rounded-xl shadow-lg border-2 border-gray-100 p-6">
                    <div className="mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">Run Summary</h3>
                      <p className="text-sm text-gray-600">Breakdown of all runs for this version</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="text-center">
                        <p className="text-2xl font-bold text-gray-900">{versionMetrics.run_summary.total_runs}</p>
                        <p className="text-sm text-gray-600">Total Runs</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-green-600">{versionMetrics.run_summary.successful_runs}</p>
                        <p className="text-sm text-gray-600">Successful</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-red-600">{versionMetrics.run_summary.failed_runs}</p>
                        <p className="text-sm text-gray-600">Failed</p>
                      </div>
                    </div>
                    {versionMetrics.run_summary.has_mixed_status && (
                      <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                        <p className="text-sm text-orange-800">
                          <strong>Note:</strong> This version has both successful and failed runs. 
                          Metrics shown above are from successful runs only.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      No Metrics Available
                    </h3>
                    <p className="text-gray-600">
                      {versionMetrics?.message || 'No MLflow metrics found for this version'}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
        </div>
      </div>
    </AppLayout>
  )
}
