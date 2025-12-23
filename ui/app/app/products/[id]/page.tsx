'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Package, Database, Settings, Play, Pause, Search, TrendingUp, BarChart3, AlertTriangle, GitBranch, FileText, Download, FileSpreadsheet, Upload, Loader2, ArrowDownToLine, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ConfirmModal, ResultModal } from '@/components/ui/modal'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient } from '@/lib/api-client'
import { DataQualityBanner } from '@/components/DataQualityBanner'
import { DataQualityViolationsDrawer } from '@/components/DataQualityViolationsDrawer'
import { DataQualityRulesEditor } from '@/components/DataQualityRulesEditor'
import { AITrustScoreDisplay } from '@/components/AITrustScoreDisplay'
import { ChunkMetadataDisplay } from '@/components/ChunkMetadataDisplay'
import { ACLManagement } from '@/components/ACLManagement'
import { useToast } from '@/components/ui/toast'

interface Product {
  id: string
  workspace_id: string
  owner_user_id: string
  name: string
  status: 'draft' | 'running' | 'ready' | 'failed' | 'failed_policy' | 'ready_with_warnings'  // M2
  current_version: number
  promoted_version?: number
  playbook_id?: string  // M1
  preprocessing_stats?: {  // M1
    sections?: number
    chunks?: number
    mid_sentence_boundary_rate?: number
    [key: string]: any
  }
  trust_score?: number  // M2
  policy_status?: string  // M2: 'passed' | 'failed' | 'warnings' | 'unknown'
  created_at: string
  updated_at?: string
}

interface DataSource {
  id: string
  workspace_id: string
  product_id: string
  type: 'web' | 'db' | 'confluence' | 'sharepoint' | 'folder'
  config: any
  last_cursor?: any
  created_at: string
  updated_at?: string
}

interface PipelineRun {
  id: string
  product_id: string
  version: number
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  started_at?: string
  finished_at?: string
  dag_run_id?: string
  metrics: any
  created_at: string
}

// MLflowMetrics interface removed - MLflow integration disabled

export default function ProductDetailPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const params = useParams()
  const productId = params.id as string
  const { addToast } = useToast()
  
  const [product, setProduct] = useState<Product | null>(null)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  // MLflow metrics state removed - MLflow integration disabled
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'ai-trust-score' | 'chunk-metadata' | 'acl' | 'datasources' | 'data-quality' | 'exports'>('overview')
  const [testingConnection, setTestingConnection] = useState<string | null>(null)
  const [ingestingDataSource, setIngestingDataSource] = useState<string | null>(null)
  const [ingestionResults, setIngestionResults] = useState<Record<string, any>>({})
  const [rawArtifacts, setRawArtifacts] = useState<any[]>([])
  const [loadingArtifacts, setLoadingArtifacts] = useState(false)
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([])
  const [loadingPipelineRuns, setLoadingPipelineRuns] = useState(false)
  const [runningPipeline, setRunningPipeline] = useState(false)
  const [pipelineConflict, setPipelineConflict] = useState<any>(null)
  const [promotingVersion, setPromotingVersion] = useState<number | null>(null)
  const [downloadingValidationSummary, setDownloadingValidationSummary] = useState(false)
  const [downloadingTrustReport, setDownloadingTrustReport] = useState(false)
  
  // Data quality states
  const [dataQualityViolations, setDataQualityViolations] = useState<any[]>([])
  const [showViolationsDrawer, setShowViolationsDrawer] = useState(false)
  const [showRulesEditor, setShowRulesEditor] = useState(false)
  const [loadingViolations, setLoadingViolations] = useState(false)
  const [existingRules, setExistingRules] = useState<any>(null)
  const [exports, setExports] = useState<any[]>([])
  const [loadingExports, setLoadingExports] = useState(false)
  const [showCreateExportModal, setShowCreateExportModal] = useState(false)
  const [creatingExport, setCreatingExport] = useState(false)
  
  // Modal states
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteDataSourceId, setDeleteDataSourceId] = useState<string | null>(null)
  const [showResultModal, setShowResultModal] = useState(false)
  const [showPipelineModal, setShowPipelineModal] = useState(false)
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
      loadDataSources()
      // MLflow metrics loading removed - MLflow integration disabled
    }
  }, [status, router, productId])

  // Load raw artifacts when product changes
  useEffect(() => {
    if (product && product.current_version > 0) {
      loadRawArtifacts()
    }
  }, [product])

  useEffect(() => {
    if (product) {
      loadPipelineRuns()
      loadDataQualityViolations()
      loadDataQualityRules()
      loadExports()
    }
  }, [product])

  // Auto-refresh pipeline runs every 10 seconds
  useEffect(() => {
    if (!product) return
    
    const interval = setInterval(() => {
      loadPipelineRuns()
    }, 10000)
    
    return () => clearInterval(interval)
  }, [product])

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

  // MLflow metrics loading removed - MLflow integration disabled

  const loadDataSources = async () => {
    try {
      const response = await apiClient.getDataSources(productId)
      
      if (response.error) {
        console.error('Failed to load data sources:', response.error)
      } else {
        setDataSources((response.data as DataSource[]) || [])
      }
    } catch (err) {
      console.error('Failed to load data sources:', err)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft': return 'bg-gray-100 text-gray-800'
      case 'running': return 'bg-blue-100 text-blue-800'
      case 'ready': return 'bg-green-100 text-green-800'
      case 'failed': return 'bg-red-100 text-red-800'
      case 'failed_policy': return 'bg-red-100 text-red-800'  // M2
      case 'ready_with_warnings': return 'bg-yellow-100 text-yellow-800'  // M2
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getDataSourceTypeIcon = (type: string) => {
    switch (type) {
      case 'web': return '🌐'
      case 'db': return '🗄️'
      case 'confluence': return '📄'
      case 'sharepoint': return '📁'
      case 'folder': return '📂'
      default: return '📊'
    }
  }

  const truncateText = (text: string, maxLength: number = 30) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  const getDataSourceDisplayInfo = (datasource: DataSource) => {
    const config = datasource.config || {}
    
    // Debug logging for confluence
    if (datasource.type === 'confluence') {
      console.log('Confluence datasource config:', config)
      console.log('Space key (singular):', config.space_key)
      console.log('Space keys (plural):', config.space_keys)
      console.log('Final space keys value:', config.space_keys || config.space_key)
      console.log('Has space keys:', !!(config.space_keys || config.space_key))
    }
    
    switch (datasource.type) {
      case 'web':
        return {
          title: 'Web Scraping',
          subtitle: config.url ? truncateText(config.url, 35) : 'No URL configured',
          details: config.selector ? `Selector: ${truncateText(config.selector, 20)}` : 'No selector',
          fullSubtitle: config.url || 'No URL configured'
        }
      case 'db':
        return {
          title: 'Database',
          subtitle: `${config.host || 'Unknown'}:${config.port || 'Unknown'}`,
          details: config.database ? `Database: ${config.database}` : 'No database specified',
          fullSubtitle: `${config.host || 'Unknown'}:${config.port || 'Unknown'}`
        }
      case 'confluence':
        // Check for both space_keys (plural) and space_key (singular) to handle different data formats
        const spaceKeys = config.space_keys || config.space_key
        const hasSpaceKeys = spaceKeys && 
          (typeof spaceKeys === 'string' ? spaceKeys.trim() : String(spaceKeys).trim())
        
        return {
          title: 'Confluence',
          subtitle: config.base_url ? truncateText(config.base_url, 35) : 'No base URL configured',
          details: hasSpaceKeys ? `Spaces: ${truncateText(String(spaceKeys), 20)}` : 'All spaces',
          fullSubtitle: config.base_url || 'No base URL configured'
        }
      case 'sharepoint':
        return {
          title: 'SharePoint',
          subtitle: config.site_url ? truncateText(config.site_url, 35) : 'No site URL configured',
          details: config.tenant_id ? `Tenant: ${truncateText(config.tenant_id, 20)}` : 'No tenant ID',
          fullSubtitle: config.site_url || 'No site URL configured'
        }
      case 'folder':
        return {
          title: 'Local Folder',
          subtitle: config.path ? truncateText(config.path, 35) : 'No path configured',
          details: config.file_types ? `Types: ${truncateText(config.file_types, 20)}` : 'All file types',
          fullSubtitle: config.path || 'No path configured'
        }
      default:
        return {
          title: 'Custom',
          subtitle: 'Custom configuration',
          details: 'Custom data source',
          fullSubtitle: 'Custom configuration'
        }
    }
  }

  const handleIngestDataSource = async (datasourceId: string) => {
    setIngestingDataSource(datasourceId)
    try {
      const response = await apiClient.syncFullDataSource(datasourceId)
      
      if (response.error) {
        setResultModalData({
          type: 'error',
          title: 'Ingestion Failed',
          message: typeof response.error === 'string' ? response.error : 'Ingestion failed'
        })
      } else {
        // Store the ingestion result
        setIngestionResults(prev => ({
          ...prev,
          [datasourceId]: response.data
        }))
        
        setResultModalData({
          type: 'success',
          title: 'Ingestion Completed',
          message: `Successfully ingested ${response.data.files} files (${(response.data.bytes / 1024 / 1024).toFixed(2)} MB) in ${response.data.duration.toFixed(2)}s`
        })
      }
      setShowResultModal(true)
    } catch (err) {
      setResultModalData({
        type: 'error',
        title: 'Ingestion Failed',
        message: 'Failed to run ingestion'
      })
      setShowResultModal(true)
    } finally {
      setIngestingDataSource(null)
    }
  }

  const handleTestConnection = async (datasourceId: string) => {
    setTestingConnection(datasourceId)
    try {
      const response = await apiClient.testConnection(datasourceId)
      
      if (response.error) {
        setResultModalData({
          type: 'error',
          title: 'Connection Test Failed',
          message: typeof response.error === 'string' ? response.error : 'Connection test failed'
        })
      } else {
        setResultModalData({
          type: response.data.ok ? 'success' : 'error',
          title: response.data.ok ? 'Connection Test Successful' : 'Connection Test Failed',
          message: typeof response.data.message === 'string' ? response.data.message : 'Connection test completed'
        })
      }
      setShowResultModal(true)
    } catch (err) {
      setResultModalData({
        type: 'error',
        title: 'Connection Test Failed',
        message: 'Failed to test connection'
      })
      setShowResultModal(true)
    } finally {
      setTestingConnection(null)
    }
  }


  const loadRawArtifacts = async () => {
    if (!product) return
    
    setLoadingArtifacts(true)
    try {
      const response = await apiClient.getRawArtifacts(product.id, product.current_version)
      if (response.data) {
        setRawArtifacts(response.data.artifacts || [])
      }
    } catch (err) {
      console.error('Failed to load raw artifacts:', err)
    } finally {
      setLoadingArtifacts(false)
    }
  }

  const loadPipelineRuns = async () => {
    if (!product) return
    
    setLoadingPipelineRuns(true)
    try {
      const response = await apiClient.getPipelineRuns(product.id, 10)
      if (response.data) {
        setPipelineRuns(response.data || [])
      }
    } catch (err) {
      console.error('Failed to load pipeline runs:', err)
    } finally {
      setLoadingPipelineRuns(false)
    }
  }

  const loadDataQualityViolations = async () => {
    if (!product) return
    
    setLoadingViolations(true)
    try {
      const response = await apiClient.get(`/data-quality/products/${product.id}/violations`)
      if (response.data) {
        setDataQualityViolations(response.data || [])
      }
    } catch (err) {
      console.error('Failed to load data quality violations:', err)
    } finally {
      setLoadingViolations(false)
    }
  }

  const loadDataQualityRules = async () => {
    if (!product) return
    
    try {
      const response = await apiClient.get(`/data-quality/products/${product.id}/rules`)
      if (response.data) {
        setExistingRules(response.data)
      }
    } catch (err) {
      console.error('Failed to load data quality rules:', err)
      // Don't show error to user, just log it
    }
  }

  const handleSaveDataQualityRules = async (rules: any) => {
    if (!product) return
    
    try {
      console.log('Saving data quality rules:', rules)
      const response = await apiClient.put(`/data-quality/products/${product.id}/rules`, { rules })
      
      if (response.error) {
        throw new Error(response.error)
      }
      
      if (response.data) {
        setResultModalData({
          type: 'success',
          title: 'Data Quality Rules Saved',
          message: 'Your data quality rules have been saved successfully.',
          details: `Rules will be applied to the next pipeline run.`
        })
        setShowResultModal(true)
      }
    } catch (err) {
      console.error('Failed to save data quality rules:', err)
      
      let errorMessage = 'Unknown error occurred'
      let errorDetails = ''
      
      if (err instanceof Error) {
        errorMessage = err.message
        // Try to extract more specific error details
        if (err.message.includes('Invalid rules format')) {
          errorDetails = 'The rules format is invalid. Please check your rule configurations.'
        } else if (err.message.includes('400')) {
          errorDetails = 'Bad request - please check your rule data.'
        } else if (err.message.includes('404')) {
          errorDetails = 'Product not found.'
        } else if (err.message.includes('500')) {
          errorDetails = 'Server error occurred while saving rules.'
        }
      }
      
      setResultModalData({
        type: 'error',
        title: 'Failed to Save Rules',
        message: errorMessage,
        details: errorDetails
      })
      setShowResultModal(true)
    }
  }

  const handleRunPipeline = async (version?: number, forceRun?: boolean) => {
    if (!product) return
    
    setRunningPipeline(true)
    try {
      const response = await apiClient.triggerPipeline(product.id, version, forceRun)
      
      if (response.error) {
        // Check if it's a conflict error
        if (response.status === 409 && response.errorData && typeof response.errorData === 'object' && response.errorData.message) {
          setPipelineConflict(response.errorData)
          setShowPipelineModal(false)
          return
        }
        
        setResultModalData({
          type: 'error',
          title: 'Pipeline Failed',
          message: typeof response.error === 'string' ? response.error : 'An unexpected error occurred'
        })
        setShowResultModal(true)
      } else {
        setResultModalData({
          type: 'success',
          title: 'Pipeline Started',
          message: `Pipeline run triggered successfully. Version: ${response.data.version}`
        })
        
        // Refresh pipeline runs
        await loadPipelineRuns()
        setShowResultModal(true)
      }
    } catch (err) {
      setResultModalData({
        type: 'error',
        title: 'Pipeline Failed',
        message: 'Failed to trigger pipeline'
      })
      setShowResultModal(true)
    } finally {
      setRunningPipeline(false)
      setShowPipelineModal(false)
    }
  }

  const handleDownloadValidationSummary = async () => {
    if (!product) return
    
    setDownloadingValidationSummary(true)
    try {
      const blob = await apiClient.downloadValidationSummary(product.id)
      if (blob) {
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `validation_summary_${product.id}.csv`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        
        addToast({
          type: 'success',
          message: 'Validation summary downloaded successfully',
        })
      }
    } catch (err) {
      addToast({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to download validation summary',
      })
    } finally {
      setDownloadingValidationSummary(false)
    }
  }

  const handleDownloadTrustReport = async () => {
    if (!product) return
    
    setDownloadingTrustReport(true)
    try {
      const blob = await apiClient.downloadTrustReport(product.id)
      if (blob) {
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `trust_report_${product.id}.pdf`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        
        addToast({
          type: 'success',
          message: 'Trust report downloaded successfully',
        })
      }
    } catch (err) {
      addToast({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to download trust report',
      })
    } finally {
      setDownloadingTrustReport(false)
    }
  }

  const handlePromoteVersion = async (version: number) => {
    if (!product) return
    
    setPromotingVersion(version)
    try {
      const response = await apiClient.promoteVersion(product.id, version)
      
      if (response.error) {
        setResultModalData({
          type: 'error',
          title: 'Promotion Failed',
          message: typeof response.error === 'string' ? response.error : 'Failed to promote version'
        })
        setShowResultModal(true)
      } else {
        setResultModalData({
          type: 'success',
          title: 'Version Promoted',
          message: `Version ${version} has been promoted to production successfully`
        })
        
        // Refresh product data to get updated promoted_version
        await loadProduct()
        setShowResultModal(true)
      }
    } catch (err) {
      setResultModalData({
        type: 'error',
        title: 'Promotion Failed',
        message: 'Failed to promote version'
      })
      setShowResultModal(true)
    } finally {
      setPromotingVersion(null)
    }
  }

  const handleEditDataSource = (datasourceId: string) => {
    // Navigate to edit page (we'll create this)
    router.push(`/app/products/${productId}/datasources/${datasourceId}/edit`)
  }

  const handleDeleteDataSource = (datasourceId: string) => {
    setDeleteDataSourceId(datasourceId)
    setShowDeleteModal(true)
  }

  const confirmDeleteDataSource = async () => {
    if (!deleteDataSourceId) return

    try {
      const response = await apiClient.deleteDataSource(deleteDataSourceId)
      
      if (response.error) {
        setResultModalData({
          type: 'error',
          title: 'Delete Failed',
          message: typeof response.error === 'string' ? response.error : 'Delete failed'
        })
      } else {
        // Reload data sources to update the list
        loadDataSources()
        setResultModalData({
          type: 'success',
          title: 'Data Source Deleted',
          message: 'Data source has been successfully deleted'
        })
      }
      setShowResultModal(true)
    } catch (err) {
      setResultModalData({
        type: 'error',
        title: 'Delete Failed',
        message: 'Failed to delete data source'
      })
      setShowResultModal(true)
    } finally {
      setShowDeleteModal(false)
      setDeleteDataSourceId(null)
    }
  }

  const loadExports = async () => {
    if (!product) return
    
    setLoadingExports(true)
    try {
      const response = await apiClient.get(`/api/v1/exports?product_id=${product.id}`)
      if (response.data) {
        setExports(response.data)
      }
    } catch (err) {
      console.error('Failed to load exports:', err)
      setExports([])
    } finally {
      setLoadingExports(false)
    }
  }

  const handleCreateExport = async (version?: number | 'prod') => {
    if (!product) return
    
    setCreatingExport(true)
    try {
      const response = await apiClient.post(`/api/v1/exports/${product.id}/create`, {
        version: version
      })
      
      if (response.data) {
        setResultModalData({
          type: 'success',
          title: 'Export Created',
          message: 'Export bundle has been created successfully',
          details: `Bundle: ${response.data.bundle_name} (${formatFileSize(response.data.size_bytes)})`
        })
        setShowResultModal(true)
        setShowCreateExportModal(false)
        // Reload exports
        loadExports()
      }
    } catch (err) {
      console.error('Failed to create export:', err)
      setResultModalData({
        type: 'error',
        title: 'Export Failed',
        message: 'Failed to create export bundle'
      })
      setShowResultModal(true)
    } finally {
      setCreatingExport(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  if (status === 'loading' || loading) {
    return (
      <AppLayout>
        <div className="p-6 flex items-center justify-center min-h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading product...</p>
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
          <span className="text-sm font-medium text-gray-900">{product.name}</span>
        </div>

        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="bg-blue-100 rounded-lg p-2 mr-4">
                <Package className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{product.name}</h1>
                <div className="flex items-center mt-1">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(product.status)}`}>
                    {product.status}
                  </span>
                  <span className="ml-3 text-sm text-gray-500">v{product.current_version}</span>
                </div>
              </div>
            </div>
            <div className="flex space-x-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => router.push(`/app/products/${productId}/edit`)}
              >
                <Settings className="h-4 w-4 mr-2" />
                Settings
              </Button>
              <Button 
                size="sm"
                onClick={() => setShowPipelineModal(true)}
                disabled={runningPipeline || dataSources.length === 0}
              >
                <Play className="h-4 w-4 mr-2" />
                Run
              </Button>
            </div>
          </div>
        </div>

        {/* Data Quality Banner */}
        {dataQualityViolations.length > 0 && (
          <div className="mb-6">
            <DataQualityBanner
              violations={dataQualityViolations}
              onViewDetails={() => setShowViolationsDrawer(true)}
            />
          </div>
        )}

        {/* Tabs */}
        <div className="mb-8">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('ai-trust-score')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'ai-trust-score'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              AI Trust Score
              {product?.trust_score !== undefined && (() => {
                // Handle both 0-1 and 0-100 formats
                const trustScore = product.trust_score || 0
                const percentage = trustScore > 1 ? trustScore : trustScore * 100
                const normalizedScore = trustScore > 1 ? trustScore / 100 : trustScore
                
                return (
                  <span className={`ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    normalizedScore >= 0.8 ? 'bg-green-100 text-green-800' :
                    normalizedScore >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {percentage.toFixed(0)}%
                  </span>
                )
              })()}
            </button>
            <button
              onClick={() => setActiveTab('chunk-metadata')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'chunk-metadata'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Chunk Metadata
            </button>
            <button
              onClick={() => setActiveTab('acl')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'acl'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Access Control
            </button>
            <button
              onClick={() => setActiveTab('datasources')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'datasources'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Data Sources ({dataSources.length})
            </button>
            <button
              onClick={() => setActiveTab('data-quality')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'data-quality'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Data Quality {dataQualityViolations.length > 0 && (
                <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                  {dataQualityViolations.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('exports')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'exports'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Exports
            </button>
          </nav>
        </div>

        {/* Content */}
        <div>
        {activeTab === 'ai-trust-score' && (
          <div className="space-y-6">
            <AITrustScoreDisplay productId={productId} />
          </div>
        )}

        {activeTab === 'chunk-metadata' && (
          <div className="space-y-6">
            <ChunkMetadataDisplay 
              productId={productId} 
              productVersion={product?.current_version}
            />
          </div>
        )}

        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Product Information</h2>
              <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Product ID</dt>
                  <dd className="mt-1 text-sm text-gray-900 font-mono">{product.id}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Status</dt>
                  <dd className="mt-1">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(product.status)}`}>
                      {product.status}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Current Version</dt>
                  <dd className="mt-1 text-sm text-gray-900">{product.current_version}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Created</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {new Date(product.created_at).toLocaleDateString()}
                  </dd>
                </div>
                {product.updated_at && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Last Updated</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {new Date(product.updated_at).toLocaleDateString()}
                    </dd>
                  </div>
                )}
                {product.playbook_id && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Preprocessing Playbook</dt>
                    <dd className="mt-1">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {product.playbook_id}
                      </span>
                    </dd>
                  </div>
                )}
                {product.trust_score !== undefined && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">AI Trust Score</dt>
                    <dd className="mt-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        (product.trust_score || 0) >= 0.8 ? 'bg-green-100 text-green-800' :
                        (product.trust_score || 0) >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {((product.trust_score || 0) * 100).toFixed(1)}%
                      </span>
                    </dd>
                  </div>
                )}
                {product.policy_status && product.policy_status !== 'unknown' && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Policy Status</dt>
                    <dd className="mt-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        product.policy_status === 'passed' ? 'bg-green-100 text-green-800' :
                        product.policy_status === 'failed' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {product.policy_status}
                      </span>
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Preprocessing Stats Section (M1) */}
            {product.preprocessing_stats && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Preprocessing Statistics</h2>
                <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-3">
                  {product.preprocessing_stats.sections !== undefined && (
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Sections Detected</dt>
                      <dd className="mt-1 text-2xl font-semibold text-gray-900">
                        {product.preprocessing_stats.sections}
                      </dd>
                    </div>
                  )}
                  {product.preprocessing_stats.chunks !== undefined && (
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Chunks Created</dt>
                      <dd className="mt-1 text-2xl font-semibold text-gray-900">
                        {product.preprocessing_stats.chunks}
                      </dd>
                    </div>
                  )}
                  {product.preprocessing_stats.mid_sentence_boundary_rate !== undefined && (
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Mid-Sentence Boundary Rate</dt>
                      <dd className="mt-1 text-2xl font-semibold text-gray-900">
                        {(product.preprocessing_stats.mid_sentence_boundary_rate * 100).toFixed(1)}%
                      </dd>
                      <p className="mt-1 text-xs text-gray-500">
                        Lower is better (indicates better chunking)
                      </p>
                    </div>
                  )}
                </dl>
              </div>
            )}

            {/* MLflow Metrics Section removed - MLflow integration disabled */}

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <Link href={`/app/products/${product.id}/datasources/new`}>
                  <div className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer">
                    <Database className="h-8 w-8 text-blue-600 mb-2" />
                    <h3 className="font-medium text-gray-900">Add Data Source</h3>
                    <p className="text-sm text-gray-600">Connect a new data source to this product</p>
                  </div>
                </Link>
                <div 
                  className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
                  onClick={() => setShowPipelineModal(true)}
                >
                  <Play className="h-8 w-8 text-green-600 mb-2" />
                  <h3 className="font-medium text-gray-900">Run Pipeline</h3>
                  <p className="text-sm text-gray-600">Execute the data processing pipeline</p>
                </div>
                <Link href={`/app/products/${productId}/playground`}>
                  <div className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer">
                    <Search className="h-8 w-8 text-purple-600 mb-2" />
                    <h3 className="font-medium text-gray-900">RAG Playground</h3>
                    <p className="text-sm text-gray-600">Search and explore your indexed data</p>
                  </div>
                </Link>
                <Link href={`/app/products/${productId}/ai-readiness`}>
                  <div className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer">
                    <TrendingUp className="h-8 w-8 text-orange-600 mb-2" />
                    <h3 className="font-medium text-gray-900">AI Readiness</h3>
                    <p className="text-sm text-gray-600">Assess and improve data quality</p>
                  </div>
                </Link>
                <Link href={`/app/products/${productId}/pipeline-metrics`}>
                  <div className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer">
                    <BarChart3 className="h-8 w-8 text-blue-600 mb-2" />
                    <h3 className="font-medium text-gray-900">Pipeline Metrics</h3>
                    <p className="text-sm text-gray-600">View detailed metrics for each version</p>
                  </div>
                </Link>
                <Link href={`/app/products/${productId}/pipeline-runs`}>
                  <div className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer">
                    <GitBranch className="h-8 w-8 text-indigo-600 mb-2" />
                    <h3 className="font-medium text-gray-900">Pipeline Runs</h3>
                    <p className="text-sm text-gray-600">Monitor and manage pipeline executions</p>
                  </div>
                </Link>
                <div 
                  className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
                  onClick={() => router.push(`/app/products/${productId}/edit`)}
                >
                  <Settings className="h-8 w-8 text-gray-600 mb-2" />
                  <h3 className="font-medium text-gray-900">Configure</h3>
                  <p className="text-sm text-gray-600">Update product settings and configuration</p>
                </div>
              </div>
            </div>

            {/* Reports & Artifacts Section (M3) */}
            {product.current_version > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Reports & Artifacts</h2>
                <p className="text-sm text-gray-600 mb-4">
                  Download AI readiness reports and validation summaries generated from pipeline runs.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Button
                    variant="outline"
                    onClick={handleDownloadValidationSummary}
                    disabled={downloadingValidationSummary || product.current_version === 0}
                    className="flex items-center justify-center gap-2"
                  >
                    {downloadingValidationSummary ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                        Downloading...
                      </>
                    ) : (
                      <>
                        <FileSpreadsheet className="h-4 w-4" />
                        Download Validation Summary (CSV)
                      </>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleDownloadTrustReport}
                    disabled={downloadingTrustReport || product.current_version === 0}
                    className="flex items-center justify-center gap-2"
                  >
                    {downloadingTrustReport ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                        Downloading...
                      </>
                    ) : (
                      <>
                        <FileText className="h-4 w-4" />
                        Download Trust Report (PDF)
                      </>
                    )}
                  </Button>
                </div>
                {product.current_version === 0 && (
                  <p className="text-sm text-gray-500 mt-3">
                    Run a pipeline to generate reports and artifacts.
                  </p>
                )}
              </div>
            )}

            {/* Pipeline Section */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Pipeline</h2>
                <Button
                  onClick={() => setShowPipelineModal(true)}
                  disabled={runningPipeline || dataSources.length === 0}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {runningPipeline ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Starting...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      Run Pipeline
                    </>
                  )}
                </Button>
              </div>
              
              {dataSources.length === 0 ? (
                <div className="text-center py-8">
                  <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No data sources</h3>
                  <p className="text-gray-600">Add data sources before running the pipeline.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <p className="text-sm text-gray-600">
                    Run the complete data processing pipeline to ingest, clean, chunk, embed, and index your data.
                  </p>
                  
                  {/* Recent Runs Table */}
                  <div>
                    <h3 className="text-md font-medium text-gray-900 mb-3">Recent Runs</h3>
                    {loadingPipelineRuns ? (
                      <div className="text-center py-4">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2"></div>
                        <p className="text-gray-600">Loading runs...</p>
                      </div>
                    ) : pipelineRuns.length === 0 ? (
                      <div className="text-center py-4">
                        <p className="text-gray-500">No pipeline runs yet</p>
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Version
                              </th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Status
                              </th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Started
                              </th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Duration
                              </th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Actions
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {pipelineRuns.map((run) => (
                              <tr key={run.id} className="hover:bg-gray-50">
                                <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                  <div className="flex items-center space-x-2">
                                    <span>v{run.version}</span>
                                    {product?.promoted_version === run.version && (
                                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                        🚀 PROD
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="px-4 py-4 whitespace-nowrap text-sm">
                                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                    run.status === 'succeeded' ? 'bg-green-100 text-green-800' :
                                    run.status === 'running' ? 'bg-blue-100 text-blue-800' :
                                    run.status === 'failed' ? 'bg-red-100 text-red-800' :
                                    'bg-yellow-100 text-yellow-800'
                                  }`}>
                                    {run.status}
                                  </span>
                                </td>
                                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                                  {run.started_at ? new Date(run.started_at).toLocaleString() : '-'}
                                </td>
                                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                                  {run.started_at && run.finished_at ? 
                                    `${Math.round((new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000)}s` :
                                    run.started_at ? 'Running...' : '-'
                                  }
                                </td>
                                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                                  <div className="flex space-x-2">
                                    {run.dag_run_id && (
                                      <a
                                        href={`http://localhost:8080/dags/primedata_simple/grid?dag_run_id=${run.dag_run_id}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:text-blue-900"
                                      >
                                        View in Airflow
                                      </a>
                                    )}
                                    {run.status === 'succeeded' && (
                                      <button
                                        onClick={() => handlePromoteVersion(run.version)}
                                        disabled={promotingVersion === run.version || product?.promoted_version === run.version}
                                        className={`text-sm px-2 py-1 rounded ${
                                          product?.promoted_version === run.version
                                            ? 'bg-green-100 text-green-800 cursor-default'
                                            : promotingVersion === run.version
                                            ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                                            : 'bg-blue-100 text-blue-800 hover:bg-blue-200'
                                        }`}
                                      >
                                        {product?.promoted_version === run.version
                                          ? '✓ Promoted'
                                          : promotingVersion === run.version
                                          ? 'Promoting...'
                                          : 'Promote to Prod'
                                        }
                                      </button>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Raw Artifacts Table */}
            {product.current_version > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">Raw Artifacts</h2>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={loadRawArtifacts}
                    disabled={loadingArtifacts}
                  >
                    {loadingArtifacts ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                        Loading...
                      </>
                    ) : (
                      'Refresh'
                    )}
                  </Button>
                </div>
                
                {loadingArtifacts ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading artifacts...</p>
                  </div>
                ) : rawArtifacts.length === 0 ? (
                  <div className="text-center py-8">
                    <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No artifacts yet</h3>
                    <p className="text-gray-600">Run the pipeline to ingest data from all data sources and see artifacts here.</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Name
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Size
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Type
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Last Modified
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {rawArtifacts.map((artifact, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {artifact.name}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {(artifact.size / 1024).toFixed(1)} KB
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {artifact.content_type ? (
                                artifact.content_type === 'application/pdf' ? 'PDF' :
                                artifact.content_type === 'text/plain' ? 'Text' :
                                artifact.content_type === 'text/html' ? 'HTML' :
                                artifact.content_type === 'application/json' ? 'JSON' :
                                artifact.content_type === 'text/csv' ? 'CSV' :
                                artifact.content_type === 'image/png' ? 'PNG Image' :
                                artifact.content_type === 'image/jpeg' ? 'JPEG Image' :
                                artifact.content_type.startsWith('image/') ? 'Image' :
                                artifact.content_type.startsWith('text/') ? 'Text' :
                                artifact.content_type.startsWith('application/') ? 'Document' :
                                artifact.content_type
                              ) : 'Unknown'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(artifact.last_modified).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              <a
                                href={artifact.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-900"
                              >
                                Download
                              </a>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'datasources' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-gray-900">Data Sources</h2>
              <Link href={`/app/products/${product.id}/datasources/new`}>
                <Button>
                  <Database className="h-4 w-4 mr-2" />
                  Add Data Source
                </Button>
              </Link>
            </div>

            {dataSources.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg shadow-sm border border-gray-200">
                <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No data sources yet</h3>
                <p className="text-gray-600 mb-6">Connect your first data source to get started.</p>
                <Link href={`/app/products/${product.id}/datasources/new`}>
                  <Button>
                    <Database className="h-4 w-4 mr-2" />
                    Add Data Source
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {dataSources.map((datasource) => {
                  const displayInfo = getDataSourceDisplayInfo(datasource)
                  return (
                    <div key={datasource.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                      <div className="flex items-start mb-3">
                        <span className="text-2xl mr-3 flex-shrink-0">{getDataSourceTypeIcon(datasource.type)}</span>
                        <div className="min-w-0 flex-1">
                          <h3 className="font-medium text-gray-900 text-sm">{displayInfo.title}</h3>
                          <p className="text-xs text-gray-600 truncate" title={displayInfo.fullSubtitle}>
                            {displayInfo.subtitle}
                          </p>
                          <p className="text-xs text-gray-500 mt-1 truncate" title={displayInfo.details}>
                            {displayInfo.details}
                          </p>
                        </div>
                      </div>
                      
                      <div className="mb-4">
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-xs text-gray-500">
                            Created {new Date(datasource.created_at).toLocaleDateString()}
                          </p>
                          <div className="flex items-center">
                            <div className="w-2 h-2 bg-green-400 rounded-full mr-1"></div>
                            <span className="text-xs text-green-600">Active</span>
                          </div>
                        </div>
                        {datasource.last_cursor && (
                          <p className="text-xs text-blue-600">
                            Last sync: {new Date(datasource.last_cursor.timestamp || datasource.updated_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex space-x-2">
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="flex-1 text-xs"
                            onClick={() => handleEditDataSource(datasource.id)}
                          >
                            Edit
                          </Button>
                          <Button 
                            size="sm" 
                            className="flex-1 text-xs"
                            onClick={() => handleTestConnection(datasource.id)}
                            disabled={testingConnection === datasource.id}
                          >
                            {testingConnection === datasource.id ? (
                              <>
                                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-1"></div>
                                Testing...
                              </>
                            ) : (
                              'Test'
                            )}
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="flex-1 text-xs text-red-600 border-red-300 hover:bg-red-50"
                            onClick={() => handleDeleteDataSource(datasource.id)}
                          >
                            Delete
                          </Button>
                        </div>
                        
                        <div className="mt-3">
                          <Button
                            variant="outline"
                            size="default"
                            className="w-full border-green-500 text-green-600 hover:bg-green-50 hover:border-green-600 hover:text-green-700 font-medium shadow-sm transition-all duration-200 hover:shadow-md"
                            onClick={() => handleIngestDataSource(datasource.id)}
                            disabled={ingestingDataSource === datasource.id}
                          >
                            {ingestingDataSource === datasource.id ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin text-green-600" />
                                <span className="text-green-600">Ingesting Data...</span>
                              </>
                            ) : (
                              <>
                                <ArrowDownToLine className="mr-2 h-4 w-4 text-green-600" />
                                <span className="text-green-600">Run Initial Ingest</span>
                              </>
                            )}
                          </Button>
                          
                          {ingestionResults[datasource.id] && (
                            <div className="mt-2 flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2">
                              <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
                              <span className="font-medium">
                                Successfully ingested {ingestionResults[datasource.id].files} file{ingestionResults[datasource.id].files !== 1 ? 's' : ''}
                              </span>
                              <span className="text-green-600">
                                ({(ingestionResults[datasource.id].bytes / 1024 / 1024).toFixed(2)} MB)
                              </span>
                              {ingestionResults[datasource.id].errors > 0 && (
                                <span className="text-orange-600 font-medium">
                                  • {ingestionResults[datasource.id].errors} error{ingestionResults[datasource.id].errors !== 1 ? 's' : ''}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
        </div>

      {/* Modals */}
      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false)
          setDeleteDataSourceId(null)
        }}
        onConfirm={confirmDeleteDataSource}
        title="Delete Data Source"
        message="Are you sure you want to delete this data source? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
      />

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

      {/* Pipeline Modal */}
      {showPipelineModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Run Pipeline</h3>
              <p className="text-sm text-gray-600 mb-4">
                Run the complete data processing pipeline for this product. This will:
              </p>
              <ul className="text-sm text-gray-600 mb-6 space-y-1">
                <li>• Automatically ingest data from all data sources</li>
                <li>• Clean and preprocess the data</li>
                <li>• Chunk documents for processing</li>
                <li>• Generate embeddings</li>
                <li>• Index to Qdrant for search</li>
                <li>• Validate and finalize</li>
              </ul>
              <div className="flex justify-end space-x-3">
                <Button
                  variant="outline"
                  onClick={() => setShowPipelineModal(false)}
                  disabled={runningPipeline}
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => handleRunPipeline()}
                  disabled={runningPipeline}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {runningPipeline ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Starting...
                    </>
                  ) : (
                    'Run Pipeline'
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pipeline Conflict Modal */}
      {pipelineConflict && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Pipeline Conflict</h3>
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-3">
                  {typeof pipelineConflict.message === 'string' ? pipelineConflict.message : 'A pipeline conflict occurred'}
                </p>
                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-yellow-800">
                        Existing Pipeline Run
                      </h3>
                      <div className="mt-2 text-sm text-yellow-700">
                        <p><strong>Status:</strong> {pipelineConflict.existing_status || 'Unknown'}</p>
                        <p><strong>Started:</strong> {pipelineConflict.existing_started_at ? new Date(pipelineConflict.existing_started_at).toLocaleString() : 'Unknown'}</p>
                        <p><strong>Run ID:</strong> {pipelineConflict.existing_run_id || 'Unknown'}</p>
                      </div>
                    </div>
                  </div>
                </div>
                <p className="text-sm text-gray-600">
                  {typeof pipelineConflict.suggestion === 'string' ? pipelineConflict.suggestion : 'Please wait for the current run to complete or use force run to override.'}
                </p>
              </div>
              <div className="flex justify-end space-x-3">
                <Button
                  variant="outline"
                  onClick={() => setPipelineConflict(null)}
                  disabled={runningPipeline}
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => {
                    setPipelineConflict(null)
                    handleRunPipeline(undefined, true)
                  }}
                  disabled={runningPipeline}
                  className="bg-orange-600 hover:bg-orange-700 text-white"
                >
                  {runningPipeline ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Starting...
                    </>
                  ) : (
                    'Force Run (Override)'
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
        )}

        {activeTab === 'data-quality' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-gray-900">Data Quality</h2>
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  onClick={() => setShowRulesEditor(true)}
                >
                  <Settings className="h-4 w-4 mr-2" />
                  Manage Rules
                </Button>
                {dataQualityViolations.length > 0 && (
                  <Button
                    variant="outline"
                    onClick={() => setShowViolationsDrawer(true)}
                  >
                    <AlertTriangle className="h-4 w-4 mr-2" />
                    View Violations ({dataQualityViolations.length})
                  </Button>
                )}
              </div>
            </div>

            {dataQualityViolations.length === 0 ? (
              <div className="text-center py-12">
                <AlertTriangle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No Quality Issues</h3>
                <p className="text-gray-600 mb-4">
                  Great! No data quality violations were detected in the latest pipeline run.
                </p>
                <Button
                  variant="outline"
                  onClick={() => setShowRulesEditor(true)}
                >
                  <Settings className="h-4 w-4 mr-2" />
                  Configure Quality Rules
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Quality Summary</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-600">
                        {dataQualityViolations.filter(v => v.severity === 'error').length}
                      </div>
                      <div className="text-sm text-gray-600">Errors</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-orange-600">
                        {dataQualityViolations.filter(v => v.severity === 'warning').length}
                      </div>
                      <div className="text-sm text-gray-600">Warnings</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">
                        {dataQualityViolations.filter(v => v.severity === 'info').length}
                      </div>
                      <div className="text-sm text-gray-600">Info</div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Violations</h3>
                  <div className="space-y-3">
                    {dataQualityViolations.slice(0, 5).map((violation) => (
                      <div key={violation.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center space-x-3">
                          <AlertTriangle className={`h-5 w-5 ${
                            violation.severity === 'error' ? 'text-red-600' :
                            violation.severity === 'warning' ? 'text-orange-600' : 'text-blue-600'
                          }`} />
                          <div>
                            <div className="font-medium text-gray-900">{violation.rule_name}</div>
                            <div className="text-sm text-gray-600">{violation.message}</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            violation.severity === 'error' ? 'bg-red-100 text-red-800' :
                            violation.severity === 'warning' ? 'bg-orange-100 text-orange-800' : 'bg-blue-100 text-blue-800'
                          }`}>
                            {violation.severity}
                          </span>
                          <div className="text-xs text-gray-500 mt-1">
                            {violation.affected_count} of {violation.total_count}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {dataQualityViolations.length > 5 && (
                    <div className="text-center mt-4">
                      <Button
                        variant="outline"
                        onClick={() => setShowViolationsDrawer(true)}
                      >
                        View All {dataQualityViolations.length} Violations
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'exports' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-gray-900">Export Bundles</h2>
              <Button
                onClick={() => setShowCreateExportModal(true)}
                disabled={!product || product.current_version === 0}
              >
                <Package className="h-4 w-4 mr-2" />
                Create Export
              </Button>
            </div>

            {!product || product.current_version === 0 ? (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
                <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No data available for export</h3>
                <p className="text-gray-600">Run the pipeline to process data before creating exports.</p>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-md font-medium text-gray-900 mb-4">Available Exports</h3>
                {loadingExports ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="text-gray-600 mt-2">Loading exports...</p>
                  </div>
                ) : exports.length === 0 ? (
                  <div className="text-center py-8">
                    <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No exports yet</h3>
                    <p className="text-gray-600 mb-4">Create your first export bundle to download processed data.</p>
                    <Button onClick={() => setShowCreateExportModal(true)}>
                      <Package className="h-4 w-4 mr-2" />
                      Create Export
                    </Button>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Bundle Name
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Version
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Size
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Created
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {exports.map((exportBundle) => (
                          <tr key={exportBundle.id}>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-gray-900">
                                {exportBundle.bundle_name}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                v{exportBundle.version}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {formatFileSize(exportBundle.size_bytes)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(exportBundle.created_at).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                              <a
                                href={exportBundle.download_url}
                                download={exportBundle.bundle_name}
                                className="text-blue-600 hover:text-blue-900"
                              >
                                Download
                              </a>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Data Quality Components */}
      <DataQualityViolationsDrawer
        isOpen={showViolationsDrawer}
        onClose={() => setShowViolationsDrawer(false)}
        violations={dataQualityViolations}
        productId={productId}
        version={product?.current_version}
      />

      <DataQualityRulesEditor
        isOpen={showRulesEditor}
        onClose={() => setShowRulesEditor(false)}
        onSave={handleSaveDataQualityRules}
        initialRules={existingRules}
        productId={productId}
      />

      {/* Create Export Modal */}
      {showCreateExportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Create Export Bundle</h3>
              <p className="text-sm text-gray-600 mb-6">
                Choose which version to export. The bundle will include chunked data, embeddings, and provenance information.
              </p>
              
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <input
                    type="radio"
                    id="current-version"
                    name="export-version"
                    value="current"
                    defaultChecked
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                  />
                  <label htmlFor="current-version" className="text-sm font-medium text-gray-700">
                    Current Version (v{product?.current_version})
                  </label>
                </div>
                
                {product?.promoted_version && product.promoted_version !== product.current_version && (
                  <div className="flex items-center space-x-3">
                    <input
                      type="radio"
                      id="promoted-version"
                      name="export-version"
                      value="prod"
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                    />
                    <label htmlFor="promoted-version" className="text-sm font-medium text-gray-700">
                      Promoted Version (v{product.promoted_version})
                    </label>
                  </div>
                )}
              </div>
              
              <div className="flex justify-end space-x-3 mt-6">
                <Button
                  variant="outline"
                  onClick={() => setShowCreateExportModal(false)}
                  disabled={creatingExport}
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => {
                    const selectedVersion = document.querySelector('input[name="export-version"]:checked')?.value
                    if (selectedVersion === 'prod') {
                      handleCreateExport('prod')
                    } else {
                      handleCreateExport()
                    }
                  }}
                  disabled={creatingExport}
                >
                  {creatingExport ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Creating...
                    </>
                  ) : (
                    <>
                      <Package className="h-4 w-4 mr-2" />
                      Create Export
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  )
}
