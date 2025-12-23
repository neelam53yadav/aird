'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Save, X, Package, Settings, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ResultModal } from '@/components/ui/modal'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient } from '@/lib/api-client'
import { getEmbeddingModelOptions, getEmbeddingDimension, requiresApiKey } from '@/lib/embedding-models'

interface Product {
  id: string
  workspace_id: string
  owner_user_id: string
  name: string
  status: 'draft' | 'running' | 'ready' | 'failed'
  current_version: number
  created_at: string
  updated_at?: string
}

export default function EditProductPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const params = useParams()
  const productId = params.id as string
  
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    status: 'draft' as 'draft' | 'running' | 'ready' | 'failed',
    // Chunking configuration
    chunking_mode: 'auto' as 'auto' | 'manual',
    chunk_size: 1000,
    chunk_overlap: 200,
    min_chunk_size: 100,
    max_chunk_size: 2000,
    chunking_strategy: 'fixed_size' as 'fixed_size' | 'semantic' | 'recursive',
    content_type: 'general',
    model_optimized: true,
    confidence_threshold: 0.7,
    // Embedding configuration
    embedder_name: 'minilm',
    embedding_dimension: 384
  })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [autoConfiguring, setAutoConfiguring] = useState(false)

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
      setLoading(true)
      const response = await apiClient.getProduct(productId)
      
      if (response.error) {
        setError(response.error)
      } else {
        const productData = response.data as Product
        setProduct(productData)

        // Derive chunking configuration (prefer resolved_settings, then manual/auto settings, then defaults)
        const cfg = (productData as any).chunking_config || {}
        const resolved = cfg.resolved_settings || cfg.manual_settings || cfg.auto_settings || cfg
        const chunkingMode = cfg.mode || 'auto'

        const derivedChunkSize = resolved.chunk_size || resolved.max_tokens || 1000
        const derivedChunkOverlap =
          resolved.chunk_overlap ??
          (resolved.overlap_sentences ? resolved.overlap_sentences * 20 : 200)
        const derivedMinChunk = resolved.min_chunk_size || 100
        const derivedMaxChunk = resolved.max_chunk_size || 2000
        const derivedStrategy = resolved.chunking_strategy || resolved.strategy || 'fixed_size'
        const derivedContentType = resolved.content_type || 'general'
        const derivedModelOptimized = resolved.model_optimized ?? true
        const derivedConfidence = resolved.confidence || resolved.analysis_confidence || 0.7
        const derivedEmbedder = resolved.embedder_name || 'minilm'
        const derivedDim = resolved.embedding_dimension || 384

        setFormData({
          name: productData.name,
          status: productData.status,
          // Load chunking configuration from product (if available)
          chunking_mode: chunkingMode,
          chunk_size: derivedChunkSize,
          chunk_overlap: derivedChunkOverlap,
          min_chunk_size: derivedMinChunk,
          max_chunk_size: derivedMaxChunk,
          chunking_strategy: derivedStrategy,
          content_type: derivedContentType,
          model_optimized: derivedModelOptimized,
          confidence_threshold: derivedConfidence,
          embedder_name: derivedEmbedder,
          embedding_dimension: derivedDim
        })
      }
    } catch (err) {
      setError('Failed to load product')
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: string, value: string | number) => {
    setFormData(prev => {
      const newData = {
        ...prev,
        [field]: value
      }
      
      // Auto-update embedding dimension based on model selection
      if (field === 'embedder_name') {
        const dimension = getEmbeddingDimension(value)
        if (dimension) {
          newData.embedding_dimension = dimension
        }
      }
      
      return newData
    })
    
    // Clear field error when user starts typing
    if (fieldErrors[field]) {
      setFieldErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
    
    // Clear general error
    if (error) {
      setError(null)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Prevent multiple submissions
    if (saving) return
    
    setSaving(true)
    setError(null)
    setFieldErrors({})
    
    // Validation
    const newFieldErrors: Record<string, string> = {}
    
    if (!formData.name.trim()) {
      newFieldErrors.name = 'Product name is required'
    }
    
    // Validate chunking configuration
    if (formData.chunk_size < 50 || formData.chunk_size > 5000) {
      newFieldErrors.chunk_size = 'Chunk size must be between 50 and 5000 characters'
    }
    
    if (formData.chunk_overlap < 0 || formData.chunk_overlap >= formData.chunk_size) {
      newFieldErrors.chunk_overlap = 'Chunk overlap must be between 0 and chunk size'
    }
    
    if (formData.min_chunk_size < 10 || formData.min_chunk_size > formData.chunk_size) {
      newFieldErrors.min_chunk_size = 'Min chunk size must be between 10 and chunk size'
    }
    
    if (formData.max_chunk_size < formData.chunk_size || formData.max_chunk_size > 10000) {
      newFieldErrors.max_chunk_size = 'Max chunk size must be between chunk size and 10000'
    }
    
    if (Object.keys(newFieldErrors).length > 0) {
      setFieldErrors(newFieldErrors)
      setSaving(false)
      
      // Focus on the first invalid field
      const firstInvalidField = Object.keys(newFieldErrors)[0]
      setTimeout(() => {
        const element = document.getElementById(firstInvalidField)
        if (element) {
          element.focus()
        }
      }, 100)
      return
    }

    try {
      const response = await apiClient.updateProduct(productId, {
        name: formData.name,
        status: formData.status,
        // Include hybrid chunking configuration
        chunking_config: {
          mode: formData.chunking_mode,
          auto_settings: {
            content_type: formData.content_type,
            model_optimized: formData.model_optimized,
            confidence_threshold: formData.confidence_threshold
          },
          manual_settings: {
            chunk_size: formData.chunk_size,
            chunk_overlap: formData.chunk_overlap,
            min_chunk_size: formData.min_chunk_size,
            max_chunk_size: formData.max_chunk_size,
            chunking_strategy: formData.chunking_strategy
          }
        },
        embedding_config: {
          embedder_name: formData.embedder_name,
          embedding_dimension: formData.embedding_dimension
        }
      })

      if (response.error) {
        setResultModalData({
          type: 'error',
          title: 'Update Failed',
          message: response.error
        })
      } else {
        setResultModalData({
          type: 'success',
          title: 'Product Updated',
          message: 'Product has been successfully updated!'
        })
        // Redirect back to product detail page after a short delay
        setTimeout(() => {
          router.push(`/app/products/${productId}`)
        }, 1500)
      }
      setShowResultModal(true)
    } catch (err) {
      setResultModalData({
        type: 'error',
        title: 'Update Failed',
        message: 'An unexpected error occurred.'
      })
      setShowResultModal(true)
    } finally {
      setSaving(false)
    }
  }

  const handleAutoConfigure = async () => {
    if (autoConfiguring) return
    
    setAutoConfiguring(true)
    setError(null)
    
    try {
      const response = await apiClient.autoConfigureChunking(productId)
      
      if (response.error) {
        setResultModalData({
          type: 'error',
          title: 'Auto-Configuration Failed',
          message: response.error
        })
      } else {
        // Update form data with the auto-configured settings
        const data = response.data
        setFormData(prev => ({
          ...prev,
          chunking_mode: 'auto',
          content_type: data.content_type,
          chunk_size: data.recommended_config.chunk_size,
          chunk_overlap: data.recommended_config.chunk_overlap,
          min_chunk_size: data.recommended_config.min_chunk_size,
          max_chunk_size: data.recommended_config.max_chunk_size,
          chunking_strategy: data.recommended_config.strategy
        }))
        
        setResultModalData({
          type: 'success',
          title: 'Auto-Configuration Complete',
          message: `Content type detected: ${data.content_type} (${(data.confidence * 100).toFixed(1)}% confidence). ${data.reasoning}`
        })
      }
      setShowResultModal(true)
    } catch (err) {
      setResultModalData({
        type: 'error',
        title: 'Auto-Configuration Failed',
        message: 'An unexpected error occurred during auto-configuration.'
      })
      setShowResultModal(true)
    } finally {
      setAutoConfiguring(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft': return 'bg-gray-100 text-gray-800'
      case 'running': return 'bg-blue-100 text-blue-800'
      case 'ready': return 'bg-green-100 text-green-800'
      case 'failed': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
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

  if (status === 'unauthenticated') {
    router.push('/')
    return null
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
          <span className="text-sm font-medium text-gray-900">Edit</span>
        </div>

        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center">
            <div className="bg-blue-100 rounded-lg p-2 mr-4">
              <Package className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Edit Product</h1>
              <p className="text-sm text-gray-500 mt-1">Update product settings and configuration</p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <Label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                Product Name
              </Label>
              <Input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className={`${fieldErrors.name ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}`}
                placeholder="Enter product name"
              />
              {fieldErrors.name && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.name}</p>
              )}
            </div>

            <div>
              <Label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-2">
                Status
              </Label>
              <select
                id="status"
                value={formData.status}
                onChange={(e) => handleInputChange('status', e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              >
                <option value="draft">Draft</option>
                <option value="running">Running</option>
                <option value="ready">Ready</option>
                <option value="failed">Failed</option>
              </select>
              <p className="mt-1 text-sm text-gray-500">
                Current status: <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(product.status)}`}>
                  {product.status}
                </span>
              </p>
            </div>

            {/* Chunking Configuration Section */}
            <div className="border-t border-gray-200 pt-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className="bg-green-100 rounded-lg p-2 mr-3">
                    <FileText className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">Chunking Configuration</h3>
                    <p className="text-sm text-gray-500">Configure how documents are split into chunks for processing</p>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleAutoConfigure}
                  disabled={autoConfiguring}
                  className="ml-4"
                >
                  {autoConfiguring ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Settings className="h-4 w-4 mr-2" />
                      Auto-Configure
                    </>
                  )}
                </Button>
              </div>

              {/* Chunking Mode Selection */}
              <div className="mb-6">
                <Label htmlFor="chunking_mode" className="block text-sm font-medium text-gray-700 mb-2">
                  Chunking Mode
                </Label>
                <div className="flex space-x-4">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="chunking_mode"
                      value="auto"
                      checked={formData.chunking_mode === 'auto'}
                      onChange={(e) => handleInputChange('chunking_mode', e.target.value)}
                      className="mr-2"
                    />
                    <span className="text-sm">Auto (AI-Optimized)</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="chunking_mode"
                      value="manual"
                      checked={formData.chunking_mode === 'manual'}
                      onChange={(e) => handleInputChange('chunking_mode', e.target.value)}
                      className="mr-2"
                    />
                    <span className="text-sm">Manual (Expert Control)</span>
                  </label>
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  {formData.chunking_mode === 'auto' 
                    ? 'AI will analyze your content and optimize chunking settings automatically'
                    : 'You have full control over chunking parameters for fine-tuning'
                  }
                </p>
              </div>

              {/* Auto Mode Settings */}
              {formData.chunking_mode === 'auto' && (
                <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                  <h4 className="text-sm font-medium text-blue-900 mb-3">Auto Configuration Settings</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="content_type" className="block text-sm font-medium text-gray-700 mb-2">
                        Content Type
                      </Label>
                      <select
                        id="content_type"
                        value={formData.content_type}
                        onChange={(e) => handleInputChange('content_type', e.target.value)}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      >
                        <option value="general">General</option>
                        <option value="legal">Legal Documents</option>
                        <option value="code">Code</option>
                        <option value="documentation">Documentation</option>
                        <option value="conversation">Conversations</option>
                        <option value="academic">Academic Papers</option>
                        <option value="technical">Technical Content</option>
                      </select>
                    </div>
                    <div>
                      <Label htmlFor="confidence_threshold" className="block text-sm font-medium text-gray-700 mb-2">
                        Confidence Threshold
                      </Label>
                      <Input
                        id="confidence_threshold"
                        type="number"
                        value={formData.confidence_threshold}
                        onChange={(e) => handleInputChange('confidence_threshold', parseFloat(e.target.value) || 0.7)}
                        min="0.1"
                        max="1.0"
                        step="0.1"
                        className="mt-1"
                      />
                      <p className="mt-1 text-sm text-gray-500">
                        Minimum confidence level for auto-configuration (0.1 - 1.0)
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Chunking Parameters - Always visible but styled differently based on mode */}
              <div className={`grid grid-cols-1 md:grid-cols-2 gap-6 ${formData.chunking_mode === 'auto' ? 'opacity-60' : ''}`}>
                <div>
                  <Label htmlFor="chunking_strategy" className="block text-sm font-medium text-gray-700 mb-2">
                    Chunking Strategy
                    {formData.chunking_mode === 'auto' && <span className="text-xs text-gray-500 ml-2">(Auto-configured)</span>}
                  </Label>
                  <select
                    id="chunking_strategy"
                    value={formData.chunking_strategy}
                    onChange={(e) => handleInputChange('chunking_strategy', e.target.value)}
                    disabled={formData.chunking_mode === 'auto'}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    <option value="fixed_size">Fixed Size</option>
                    <option value="semantic">Semantic</option>
                    <option value="recursive">Recursive</option>
                  </select>
                  <p className="mt-1 text-sm text-gray-500">
                    Fixed Size: Split by character count. Semantic: Split by meaning. Recursive: Hierarchical splitting.
                  </p>
                </div>

                <div>
                  <Label htmlFor="chunk_size" className="block text-sm font-medium text-gray-700 mb-2">
                    Chunk Size (characters)
                    {formData.chunking_mode === 'auto' && <span className="text-xs text-gray-500 ml-2">(Auto-configured)</span>}
                  </Label>
                  <Input
                    id="chunk_size"
                    type="number"
                    value={formData.chunk_size}
                    onChange={(e) => handleInputChange('chunk_size', parseInt(e.target.value) || 0)}
                    disabled={formData.chunking_mode === 'auto'}
                    className={`${fieldErrors.chunk_size ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''} disabled:bg-gray-100 disabled:cursor-not-allowed`}
                    placeholder="1000"
                    min="50"
                    max="5000"
                  />
                  {fieldErrors.chunk_size && (
                    <p className="mt-1 text-sm text-red-600">{fieldErrors.chunk_size}</p>
                  )}
                  <p className="mt-1 text-sm text-gray-500">
                    Target size for each chunk (50-5000 characters)
                  </p>
                </div>

                <div>
                  <Label htmlFor="chunk_overlap" className="block text-sm font-medium text-gray-700 mb-2">
                    Chunk Overlap (characters)
                    {formData.chunking_mode === 'auto' && <span className="text-xs text-gray-500 ml-2">(Auto-configured)</span>}
                  </Label>
                  <Input
                    id="chunk_overlap"
                    type="number"
                    value={formData.chunk_overlap}
                    onChange={(e) => handleInputChange('chunk_overlap', parseInt(e.target.value) || 0)}
                    disabled={formData.chunking_mode === 'auto'}
                    className={`${fieldErrors.chunk_overlap ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''} disabled:bg-gray-100 disabled:cursor-not-allowed`}
                    placeholder="200"
                    min="0"
                    max={formData.chunk_size - 1}
                  />
                  {fieldErrors.chunk_overlap && (
                    <p className="mt-1 text-sm text-red-600">{fieldErrors.chunk_overlap}</p>
                  )}
                  <p className="mt-1 text-sm text-gray-500">
                    Overlap between consecutive chunks (0 to chunk size - 1)
                  </p>
                </div>

                <div>
                  <Label htmlFor="min_chunk_size" className="block text-sm font-medium text-gray-700 mb-2">
                    Minimum Chunk Size (characters)
                    {formData.chunking_mode === 'auto' && <span className="text-xs text-gray-500 ml-2">(Auto-configured)</span>}
                  </Label>
                  <Input
                    id="min_chunk_size"
                    type="number"
                    value={formData.min_chunk_size}
                    onChange={(e) => handleInputChange('min_chunk_size', parseInt(e.target.value) || 0)}
                    disabled={formData.chunking_mode === 'auto'}
                    className={`${fieldErrors.min_chunk_size ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''} disabled:bg-gray-100 disabled:cursor-not-allowed`}
                    placeholder="100"
                    min="10"
                    max={formData.chunk_size}
                  />
                  {fieldErrors.min_chunk_size && (
                    <p className="mt-1 text-sm text-red-600">{fieldErrors.min_chunk_size}</p>
                  )}
                  <p className="mt-1 text-sm text-gray-500">
                    Minimum acceptable chunk size (10 to chunk size)
                  </p>
                </div>

                <div>
                  <Label htmlFor="max_chunk_size" className="block text-sm font-medium text-gray-700 mb-2">
                    Maximum Chunk Size (characters)
                    {formData.chunking_mode === 'auto' && <span className="text-xs text-gray-500 ml-2">(Auto-configured)</span>}
                  </Label>
                  <Input
                    id="max_chunk_size"
                    type="number"
                    value={formData.max_chunk_size}
                    onChange={(e) => handleInputChange('max_chunk_size', parseInt(e.target.value) || 0)}
                    disabled={formData.chunking_mode === 'auto'}
                    className={`${fieldErrors.max_chunk_size ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''} disabled:bg-gray-100 disabled:cursor-not-allowed`}
                    placeholder="2000"
                    min={formData.chunk_size}
                    max="10000"
                  />
                  {fieldErrors.max_chunk_size && (
                    <p className="mt-1 text-sm text-red-600">{fieldErrors.max_chunk_size}</p>
                  )}
                  <p className="mt-1 text-sm text-gray-500">
                    Maximum acceptable chunk size (chunk size to 10000)
                  </p>
                </div>
              </div>
            </div>

            {/* Embedding Configuration Section */}
            <div className="border-t border-gray-200 pt-6">
              <div className="flex items-center mb-4">
                <div className="bg-purple-100 rounded-lg p-2 mr-3">
                  <Settings className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">Embedding Configuration</h3>
                  <p className="text-sm text-gray-500">Configure how text is converted to vector embeddings</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label htmlFor="embedder_name" className="block text-sm font-medium text-gray-700 mb-2">
                    Embedding Model
                  </Label>
                  <select
                    id="embedder_name"
                    value={formData.embedder_name}
                    onChange={(e) => handleInputChange('embedder_name', e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  >
                    {getEmbeddingModelOptions().map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-sm text-gray-500">
                    Choose the embedding model for vector generation
                  </p>
                </div>

                <div>
                  <Label htmlFor="embedding_dimension" className="block text-sm font-medium text-gray-700 mb-2">
                    Embedding Dimension
                  </Label>
                  <Input
                    id="embedding_dimension"
                    type="number"
                    value={formData.embedding_dimension}
                    onChange={(e) => handleInputChange('embedding_dimension', parseInt(e.target.value) || 0)}
                    placeholder="384"
                    min="128"
                    max="2048"
                    disabled
                  />
                  <p className="mt-1 text-sm text-gray-500">
                    Vector dimension (automatically set based on model)
                  </p>
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200">
              <Link href={`/app/products/${productId}`}>
                <Button type="button" variant="outline" disabled={saving}>
                  <X className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
              </Link>
              <Button type="submit" disabled={saving}>
                {saving ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </form>
        </div>

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
