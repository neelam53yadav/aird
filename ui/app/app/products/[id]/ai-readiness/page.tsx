'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, CheckCircle, AlertTriangle, XCircle, TrendingUp, Settings, RefreshCw, Eye, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ResultModal } from '@/components/ui/modal'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient } from '@/lib/api-client'

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

interface DataQualityMetrics {
  total_documents: number
  total_chunks: number
  avg_chunk_size: number
  min_chunk_size: number
  max_chunk_size: number
  empty_chunks: number
  duplicate_chunks: number
  encoding_issues: number
  low_quality_chunks: number
}

interface AIReadinessScore {
  overall_score: number
  data_quality_score: number
  chunk_quality_score: number
  embedding_quality_score: number
  coverage_score: number
  recommendations: string[]
  critical_issues: string[]
}

interface AIReadinessResponse {
  product_id: string
  version: number
  collection_name: string
  metrics: DataQualityMetrics
  score: AIReadinessScore
  sample_chunks: Array<{
    text: string
    source_file: string
    chunk_index: number
    quality_issues: string[]
  }>
  last_assessed: string
}

export default function AIReadinessPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const params = useParams()
  const productId = params.id as string
  
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [assessing, setAssessing] = useState(false)
  const [improving, setImproving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aiReadiness, setAIReadiness] = useState<AIReadinessResponse | null>(null)
  const [useVersion, setUseVersion] = useState<'current' | 'prod'>('current')
  
  // Modal states
  const [showResultModal, setShowResultModal] = useState(false)
  const [resultModalData, setResultModalData] = useState<{
    type: 'success' | 'error' | 'warning' | 'info'
    title: string
    message: string
  } | null>(null)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/')
      return
    }

    if (status === 'authenticated' && productId) {
      loadProduct()
    }
  }, [status, router, productId])

  const loadProduct = async () => {
    try {
      const response = await apiClient.getProduct(productId)
      
      if (response.error) {
        setError(response.error)
      } else {
        setProduct(response.data as Product)
      }
    } catch (err) {
      setError('Failed to load product')
    } finally {
      setLoading(false)
    }
  }

  const assessAIReadiness = async () => {
    setAssessing(true)
    try {
      const response = await apiClient.assessAIReadiness(productId, useVersion)
      
      if (response.error) {
        setResultModalData({
          type: 'error',
          title: 'Assessment Failed',
          message: response.error
        })
        setShowResultModal(true)
      } else {
        setAIReadiness(response.data as AIReadinessResponse)
        setResultModalData({
          type: 'success',
          title: 'Assessment Complete',
          message: `AI readiness assessment completed successfully for ${useVersion === 'prod' ? 'production' : 'current'} version`
        })
        setShowResultModal(true)
      }
    } catch (err) {
      setResultModalData({
        type: 'error',
        title: 'Assessment Failed',
        message: 'An unexpected error occurred during assessment'
      })
      setShowResultModal(true)
    } finally {
      setAssessing(false)
    }
  }

  const improveAIReadiness = async () => {
    setImproving(true)
    try {
      const config = {
        min_chunk_size: 100,
        max_chunk_size: 2000,
        chunk_overlap: 200,
        remove_duplicates: true,
        clean_encoding: true,
        remove_low_quality: true,
        quality_threshold: 0.7
      }
      
      const response = await apiClient.improveAIReadiness(productId, config)
      
      if (response.error) {
        setResultModalData({
          type: 'error',
          title: 'Improvement Failed',
          message: response.error
        })
        setShowResultModal(true)
      } else {
        const result = response.data
        let message = ''
        let type: 'success' | 'error' | 'warning' | 'info' = 'success'
        
        if (result.status === 'completed') {
          message = `Improvement completed! ${result.improvements_applied} chunks improved, ${result.chunks_removed} chunks removed, ${result.chunks_fixed} chunks fixed.`
          type = 'success'
        } else if (result.status === 'no_improvements') {
          message = `No improvements needed. ${result.chunks_removed} low-quality chunks were removed.`
          type = 'info'
        } else if (result.status === 'no_data') {
          message = 'No data found to improve.'
          type = 'warning'
        } else {
          message = result.message || 'Improvement completed with issues.'
          type = 'warning'
        }
        
        setResultModalData({
          type: type,
          title: 'Improvement Complete',
          message: message
        })
        setShowResultModal(true)
        
        // Refresh the assessment to show updated scores
        setTimeout(() => {
          assessAIReadiness()
        }, 2000)
      }
    } catch (err) {
      setResultModalData({
        type: 'error',
        title: 'Improvement Failed',
        message: 'An unexpected error occurred during improvement'
      })
      setShowResultModal(true)
    } finally {
      setImproving(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600 bg-green-100'
    if (score >= 6) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  const getScoreIcon = (score: number) => {
    if (score >= 8) return <CheckCircle className="h-5 w-5" />
    if (score >= 6) return <AlertTriangle className="h-5 w-5" />
    return <XCircle className="h-5 w-5" />
  }

  if (status === 'loading' || loading) {
    return (
      <AppLayout>
        <div className="p-6 flex items-center justify-center min-h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading AI readiness dashboard...</p>
          </div>
        </div>
      </AppLayout>
    )
  }

  if (error || !product) {
    return (
      <AppLayout>
        <div className="p-6 flex items-center justify-center min-h-96">
          <div className="text-center">
            <p className="text-red-600 mb-4">Error: {error || 'Product not found'}</p>
            <Link href="/app/products">
              <Button>Back to Products</Button>
            </Link>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="p-6">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center mb-6">
          <Link href="/app/products" className="flex items-center text-sm text-gray-500 hover:text-gray-700 transition-colors">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Products
          </Link>
          <span className="mx-2 text-gray-400">/</span>
          <Link href={`/app/products/${productId}`} className="text-sm text-gray-500 hover:text-gray-700 transition-colors">
            {product.name}
          </Link>
          <span className="mx-2 text-gray-400">/</span>
          <span className="text-sm font-medium text-gray-900">AI Readiness</span>
        </div>

        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="bg-purple-100 rounded-lg p-2 mr-4">
                <TrendingUp className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">AI Readiness Dashboard</h1>
                <p className="text-sm text-gray-500 mt-1">Assess and improve data quality for optimal AI performance</p>
              </div>
            </div>
            <div className="flex space-x-3">
              {/* Data Source Toggle */}
              <div className="flex items-center space-x-4 mr-4">
                <span className="text-sm font-medium text-gray-700">Data Source:</span>
                <div className="flex space-x-2">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="useVersion"
                      value="current"
                      checked={useVersion === 'current'}
                      onChange={(e) => setUseVersion(e.target.value as 'current' | 'prod')}
                      className="mr-2"
                      disabled={assessing || improving}
                    />
                    <span className="text-sm text-gray-700">Current (v{product.current_version})</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="useVersion"
                      value="prod"
                      checked={useVersion === 'prod'}
                      onChange={(e) => setUseVersion(e.target.value as 'current' | 'prod')}
                      className="mr-2"
                      disabled={assessing || improving || !product.promoted_version}
                    />
                    <span className={`text-sm ${!product.promoted_version ? 'text-gray-400' : 'text-gray-700'}`}>
                      Production {product.promoted_version ? `(v${product.promoted_version})` : '(Not Available)'}
                    </span>
                  </label>
                </div>
              </div>
              
              <Button
                onClick={assessAIReadiness}
                disabled={assessing || (useVersion === 'current' && product.current_version <= 0) || (useVersion === 'prod' && !product.promoted_version)}
                variant="outline"
              >
                {assessing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                    Assessing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Assess
                  </>
                )}
              </Button>
              {aiReadiness && aiReadiness.score.overall_score < 8 && (
                <Button
                  onClick={improveAIReadiness}
                  disabled={improving}
                  className="bg-purple-600 hover:bg-purple-700 text-white"
                >
                  {improving ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Improving...
                    </>
                  ) : (
                    <>
                      <Settings className="h-4 w-4 mr-2" />
                      Improve
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Status Banner */}
        {product.current_version <= 0 && (
          <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-center">
              <AlertTriangle className="h-5 w-5 text-yellow-400 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-yellow-800">No Data Available</h3>
                <p className="text-sm text-yellow-700 mt-1">Please run a pipeline first to index data before assessing AI readiness.</p>
              </div>
            </div>
          </div>
        )}

        {!aiReadiness ? (
          /* Initial State */
          <div className="text-center py-12">
            <TrendingUp className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Ready to Assess AI Readiness</h3>
            <p className="text-gray-600 mb-6">Click "Assess" to analyze your data quality and get recommendations for AI optimization.</p>
            <Button
              onClick={assessAIReadiness}
              disabled={assessing || (useVersion === 'current' && product.current_version <= 0) || (useVersion === 'prod' && !product.promoted_version)}
              className="bg-purple-600 hover:bg-purple-700 text-white"
            >
              {assessing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Assessing...
                </>
              ) : (
                <>
                  <TrendingUp className="h-4 w-4 mr-2" />
                  Start Assessment
                </>
              )}
            </Button>
          </div>
        ) : (
          /* Assessment Results */
          <div className="space-y-6">
            {/* Overall Score */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Overall AI Readiness Score</h2>
                  <p className="text-sm text-gray-600 mt-1">
                    📊 Assessing {useVersion === 'prod' ? 'production' : 'current'} data • 
                    <span className="ml-1 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      v{aiReadiness.version}
                    </span>
                  </p>
                </div>
                <div className={`flex items-center px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(aiReadiness.score.overall_score)}`}>
                  {getScoreIcon(aiReadiness.score.overall_score)}
                  <span className="ml-2">{aiReadiness.score.overall_score}/10</span>
                </div>
              </div>
              
              <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
                <div 
                  className={`h-3 rounded-full transition-all duration-500 ${
                    aiReadiness.score.overall_score >= 8 ? 'bg-green-500' :
                    aiReadiness.score.overall_score >= 6 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${(aiReadiness.score.overall_score / 10) * 100}%` }}
                ></div>
              </div>
              
              <p className="text-sm text-gray-600">
                Last assessed: {new Date(aiReadiness.last_assessed).toLocaleString()}
              </p>
            </div>

            {/* Score Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-900">Data Quality</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getScoreColor(aiReadiness.score.data_quality_score)}`}>
                    {aiReadiness.score.data_quality_score}/10
                  </span>
                </div>
                <p className="text-xs text-gray-600">Encoding, duplicates, empty chunks</p>
              </div>
              
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-900">Chunk Quality</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getScoreColor(aiReadiness.score.chunk_quality_score)}`}>
                    {aiReadiness.score.chunk_quality_score}/10
                  </span>
                </div>
                <p className="text-xs text-gray-600">Size distribution, content quality</p>
              </div>
              
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-900">Embedding Quality</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getScoreColor(aiReadiness.score.embedding_quality_score)}`}>
                    {aiReadiness.score.embedding_quality_score}/10
                  </span>
                </div>
                <p className="text-xs text-gray-600">Vector representation quality</p>
              </div>
              
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-900">Coverage</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getScoreColor(aiReadiness.score.coverage_score)}`}>
                    {aiReadiness.score.coverage_score}/10
                  </span>
                </div>
                <p className="text-xs text-gray-600">Document and chunk volume</p>
              </div>
            </div>

            {/* Metrics */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Data Quality Metrics</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">{aiReadiness.metrics.total_documents}</div>
                  <div className="text-sm text-gray-600">Documents</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">{aiReadiness.metrics.total_chunks}</div>
                  <div className="text-sm text-gray-600">Chunks</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">{Math.round(aiReadiness.metrics.avg_chunk_size)}</div>
                  <div className="text-sm text-gray-600">Avg Chunk Size</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">{aiReadiness.metrics.duplicate_chunks}</div>
                  <div className="text-sm text-gray-600">Duplicates</div>
                </div>
              </div>
            </div>

            {/* Critical Issues */}
            {aiReadiness.score.critical_issues.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-start">
                  <XCircle className="h-5 w-5 text-red-400 mt-0.5 mr-3 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-red-800">Critical Issues</h3>
                    <div className="mt-2 space-y-3">
                      {aiReadiness.score.critical_issues.map((issue, index) => (
                        <div key={index} className="flex items-center justify-between bg-white rounded-lg p-3 border border-red-100">
                          <p className="text-sm text-red-700 flex-1">{issue}</p>
                          <div className="ml-3">
                            <Button
                              size="sm"
                              className="text-xs bg-red-600 hover:bg-red-700 text-white"
                              onClick={() => improveAIReadiness()}
                              disabled={improving}
                            >
                              {improving ? 'Fixing...' : 'Fix Now'}
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Recommendations */}
            {aiReadiness.score.recommendations.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start">
                  <AlertTriangle className="h-5 w-5 text-blue-400 mt-0.5 mr-3 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-blue-800">Recommendations</h3>
                    <div className="mt-2 space-y-3">
                      {aiReadiness.score.recommendations.map((recommendation, index) => (
                        <div key={index} className="flex items-center justify-between bg-white rounded-lg p-3 border border-blue-100">
                          <p className="text-sm text-blue-700 flex-1">{recommendation}</p>
                          <div className="ml-3 flex space-x-2">
                            {recommendation.includes('duplicate') && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-xs"
                                onClick={() => improveAIReadiness()}
                                disabled={improving}
                              >
                                {improving ? 'Processing...' : 'Remove Duplicates'}
                              </Button>
                            )}
                            {recommendation.includes('chunk size') && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-xs"
                                onClick={() => improveAIReadiness()}
                                disabled={improving}
                              >
                                {improving ? 'Processing...' : 'Fix Chunk Sizes'}
                              </Button>
                            )}
                            {recommendation.includes('low-quality') && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-xs"
                                onClick={() => improveAIReadiness()}
                                disabled={improving}
                              >
                                {improving ? 'Processing...' : 'Clean Quality'}
                              </Button>
                            )}
                            {recommendation.includes('data sources') && (
                              <Link href={`/app/products/${productId}/datasources/new`}>
                                <Button
                                  size="sm"
                                  className="text-xs bg-blue-600 hover:bg-blue-700 text-white"
                                >
                                  Add Data Source
                                </Button>
                              </Link>
                            )}
                            {recommendation.includes('chunking strategy') && (
                              <Link href={`/app/products/${productId}/edit`}>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="text-xs"
                                >
                                  Configure Chunking
                                </Button>
                              </Link>
                            )}
                            {!recommendation.includes('duplicate') && 
                             !recommendation.includes('chunk size') && 
                             !recommendation.includes('low-quality') && 
                             !recommendation.includes('data sources') && 
                             !recommendation.includes('chunking strategy') && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-xs"
                                onClick={() => improveAIReadiness()}
                                disabled={improving}
                              >
                                {improving ? 'Processing...' : 'Apply Fix'}
                              </Button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Sample Chunks */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Sample Chunks</h2>
              <div className="space-y-4">
                {aiReadiness.sample_chunks.map((chunk, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center">
                        <FileText className="h-4 w-4 text-gray-400 mr-2" />
                        <span className="text-sm font-medium text-gray-900">
                          {chunk.source_file.split('/').pop()} - Chunk {chunk.chunk_index}
                        </span>
                      </div>
                      {chunk.quality_issues.length > 0 && (
                        <div className="flex space-x-1">
                          {chunk.quality_issues.map((issue, issueIndex) => (
                            <span key={issueIndex} className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded">
                              {issue}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <p className="text-sm text-gray-700">{chunk.text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Result Modal */}
        {resultModalData && (
          <ResultModal
            isOpen={showResultModal}
            onClose={() => {
              setShowResultModal(false)
              setResultModalData(null)
            }}
            title={resultModalData.title}
            message={resultModalData.message}
            type={resultModalData.type}
          />
        )}
      </div>
    </AppLayout>
  )
}
