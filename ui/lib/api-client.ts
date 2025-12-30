/**
 * API Client for PrimeData Backend
 * 
 * This module provides a centralized API client for making requests to the backend API.
 * All requests automatically include authentication cookies and handle errors consistently.
 */

type ApiResponse<T = any> = {
  data?: T
  error?: string
  status?: number
  errorData?: any
}

// Type definitions for API responses
export type PlaybookInfo = {
  id: string
  description?: string
}

export type PlaybookResponse = {
  id: string
  description?: string
  config?: Record<string, any>
}

export type ProductInsightsResponse = {
  insights?: any
  recommendations?: any[]
  [key: string]: any
}

export type TrustMetricsResponse = {
  metrics?: Record<string, number>
  [key: string]: any
}

export type CostEstimate = {
  estimated_cost?: number
  token_count?: number
  [key: string]: any
}

export type ChunkMetadata = {
  chunk_id?: string
  metadata?: Record<string, any>
  [key: string]: any
}

export type HealthCheckResponse = {
  status?: string
  [key: string]: any
}

export type BillingLimitsResponse = {
  plan: string
  limits: {
    max_products: number
    max_data_sources_per_product: number
    max_pipeline_runs_per_month: number
    max_vectors: number
    schedule_frequency: string
  }
  usage: {
    products: number
    data_sources: number
    pipeline_runs_this_month: number
    vectors: number
  }
}

export type CheckoutSessionResponse = {
  checkout_url: string
  session_id: string
}

export type BillingPortalResponse = {
  portal_url: string
}

export type TeamMemberResponse = {
  id: string
  user_id: string
  email: string
  name: string
  role: string
  created_at: string
}

export type ACL = {
  id?: string
  name?: string
  description?: string
  product_id?: string
  user_id?: string
  access_type?: string
  index_scope?: string
  doc_scope?: string
  field_scope?: string
  rules?: Array<Record<string, any>>
  created_at?: string
  updated_at?: string
  [key: string]: any
}

export type PipelineRun = {
  id?: string
  status?: string
  [key: string]: any
}

class ApiClient {
  private baseUrl: string

  constructor() {
    // Get API base URL from environment variable, with fallback
    this.baseUrl = process.env.NEXT_PUBLIC_API_BASE || 
                   process.env.NEXT_PUBLIC_API_URL || 
                   'http://localhost:8000'
  }

  /**
   * Generic GET request
   */
  async get<T = any>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>('GET', path)
  }

  /**
   * Generic POST request
   */
  async post<T = any>(path: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>('POST', path, body)
  }

  /**
   * Generic PUT request
   */
  async put<T = any>(path: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', path, body)
  }

  /**
   * Generic PATCH request
   */
  async patch<T = any>(path: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>('PATCH', path, body)
  }

  /**
   * Generic DELETE request
   */
  async delete<T = any>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', path)
  }

  /**
   * Base request method that handles all HTTP requests
   */
  private async request<T>(
    method: string,
    path: string,
    body?: any
  ): Promise<ApiResponse<T>> {
    try {
      // Ensure path starts with /api/v1 or includes the full path
      const url = path.startsWith('http') 
        ? path 
        : path.startsWith('/') 
          ? `${this.baseUrl}${path}`
          : `${this.baseUrl}/api/v1/${path}`

      // Read token from cookie (handle URL encoding)
      // Cookie is NOT httpOnly so we can read it for cross-origin requests
      const cookieToken = (() => {
        const cookie = document.cookie
          .split('; ')
          .find(row => row.startsWith('primedata_api_token='))
        if (!cookie) return null
        const value = cookie.split('=').slice(1).join('=') // Handle = in token
        return value ? decodeURIComponent(value) : null
      })()

      // Always include Authorization header if we have a token
      // This is required for cross-origin requests (different port = different origin)
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }
      
      if (cookieToken) {
        headers['Authorization'] = `Bearer ${cookieToken}`
      }

      const options: RequestInit = {
        method,
        headers,
        credentials: 'include', // Include cookies for authentication (backup)
      }

      if (body) {
        options.body = JSON.stringify(body)
      }

      const response = await fetch(url, options)
      const status = response.status

      // Handle blob responses (for downloads)
      if (response.headers.get('content-type')?.includes('application/octet-stream') ||
          response.headers.get('content-type')?.includes('application/pdf') ||
          response.headers.get('content-type')?.includes('text/csv')) {
        if (!response.ok) {
          const errorText = await response.text()
          return {
            error: `Request failed: ${errorText}`,
            status,
          }
        }
        const blob = await response.blob()
        return { data: blob as any, status }
      }

      // Handle JSON responses
      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        const data = await response.json()

        if (!response.ok) {
          // Handle FastAPI validation errors (array of error objects)
          let errorMessage: string
          if (Array.isArray(data.detail)) {
            // Format validation errors
            errorMessage = data.detail
              .map((err: any) => {
                const field = err.loc?.slice(1).join('.') || 'field'
                return `${field}: ${err.msg}`
              })
              .join('; ')
          } else if (typeof data.detail === 'string') {
            errorMessage = data.detail
          } else if (typeof data.detail === 'object' && data.detail !== null) {
            // Handle structured error details (like 409 conflicts)
            if (data.detail.message) {
              errorMessage = data.detail.message
            } else {
              errorMessage = `Request failed with status ${status}`
            }
            // Return the detail object as errorData for structured error handling
            return {
              error: errorMessage,
              status,
              errorData: data.detail, // Use detail object directly for structured errors
            }
          } else if (data.message) {
            errorMessage = data.message
          } else {
            errorMessage = `Request failed with status ${status}`
          }
          
          return {
            error: errorMessage,
            status,
            errorData: data.detail || data, // Include full error data
          }
        }

        return { data, status }
      }

      // Handle text responses
      const text = await response.text()
      if (!response.ok) {
        return {
          error: text || `Request failed with status ${status}`,
          status,
        }
      }

      return { data: text as any, status }
    } catch (error) {
      console.error('API request failed:', error)
      return {
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      }
    }
  }

  // Health Check API
  async getHealthCheck(): Promise<ApiResponse> {
    return this.get('/api/v1/health')
  }

  // Products API
  async getProducts(): Promise<ApiResponse> {
    return this.get('/api/v1/products')
  }

  async getProduct(productId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/products/${productId}`)
  }

  async updateProduct(productId: string, data: any): Promise<ApiResponse> {
    return this.patch(`/api/v1/products/${productId}`, data)
  }

  async createProduct(data: any): Promise<ApiResponse> {
    return this.post('/api/v1/products', data)
  }

  async createProductWithPlaybook(
    workspaceId: string,
    name: string,
    playbookId?: string,
    chunkingConfig?: any
  ): Promise<ApiResponse> {
    return this.post('/api/v1/products', {
      workspace_id: workspaceId,
      name: name,
      playbook_id: playbookId || null,
      chunking_config: chunkingConfig || null,
    })
  }

  async deleteProduct(productId: string): Promise<ApiResponse> {
    return this.delete(`/api/v1/products/${productId}`)
  }

  async autoConfigureChunking(productId: string): Promise<ApiResponse> {
    return this.post(`/api/v1/products/${productId}/auto-configure-chunking`)
  }

  async promoteVersion(productId: string, version: number): Promise<ApiResponse> {
    return this.post(`/api/v1/products/${productId}/promote`, { version })
  }

  // Data Sources API
  async getDataSources(productId?: string): Promise<ApiResponse> {
    const path = productId 
      ? `/api/v1/datasources?product_id=${productId}`
      : '/api/v1/datasources'
    return this.get(path)
  }

  async getDataSource(datasourceId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/datasources/${datasourceId}`)
  }

  async createDataSource(data: any): Promise<ApiResponse> {
    return this.post('/api/v1/datasources', data)
  }

  async updateDataSource(datasourceId: string, data: any): Promise<ApiResponse> {
    return this.put(`/api/v1/datasources/${datasourceId}`, data)
  }

  async deleteDataSource(datasourceId: string): Promise<ApiResponse> {
    return this.delete(`/api/v1/datasources/${datasourceId}`)
  }

  async syncFullDataSource(datasourceId: string, version?: number): Promise<ApiResponse> {
    return this.post(`/api/v1/datasources/${datasourceId}/sync-full`, {
      version: version || null
    })
  }

  async testConnection(datasourceId: string): Promise<ApiResponse> {
    return this.post(`/api/v1/datasources/${datasourceId}/test-connection`)
  }

  async uploadFilesToDataSource(datasourceId: string, files: File[]): Promise<ApiResponse> {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    
    // Use fetch directly since we need FormData
    try {
      const url = `${this.baseUrl}/api/v1/datasources/${datasourceId}/upload-files`
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      })
      
      const status = response.status
      if (!response.ok) {
        const errorText = await response.text()
        return {
          error: `Upload failed: ${errorText}`,
          status,
        }
      }
      
      const data = await response.json()
      return { data, status }
    } catch (error) {
      console.error('File upload failed:', error)
      return {
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      }
    }
  }

  async testConfig(type: string, config: any): Promise<ApiResponse> {
    return this.post('/api/v1/datasources/test-config', {
      type: type,
      config: config,
    })
  }

  // Pipeline API
  async triggerPipeline(productId: string, version?: number, forceRun?: boolean): Promise<ApiResponse> {
    return this.post('/api/v1/pipeline/run', {
      product_id: productId,
      version: version || null,
      force_run: forceRun || false,
    })
  }

  async getPipelineRuns(productId: string, limit: number = 10): Promise<ApiResponse> {
    return this.get(`/api/v1/pipeline/runs?product_id=${productId}&limit=${limit}`)
  }

  async syncPipelineRuns(productId: string): Promise<ApiResponse> {
    return this.post(`/api/v1/pipeline/runs/sync`, { product_id: productId })
  }

  async cancelPipelineRun(runId: string): Promise<ApiResponse> {
    return this.patch(`/api/v1/pipeline/runs/${runId}`, {
      status: 'failed',
      finished_at: new Date().toISOString(),
      metrics: {
        cancelled_reason: 'Manually cancelled by user'
      }
    })
  }

  // Artifacts API
  async getRawArtifacts(productId: string, version: number): Promise<ApiResponse> {
    return this.get(`/api/v1/artifacts/raw?product_id=${productId}&version=${version}`)
  }

  // Analytics & Insights API
  async getProductInsights(productId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/analytics/products/${productId}/insights`)
  }

  async getTrustMetrics(productId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/analytics/products/${productId}/trust-metrics`)
  }

  // Downloads
  async downloadValidationSummary(productId: string): Promise<Blob | null> {
    const response = await this.get<Blob>(`/api/v1/products/${productId}/validation-summary`)
    return response.data || null
  }

  async downloadTrustReport(productId: string): Promise<Blob | null> {
    const response = await this.get<Blob>(`/api/v1/products/${productId}/trust-report`)
    return response.data || null
  }

  // Workspaces API
  async getWorkspaces(): Promise<ApiResponse> {
    return this.get('/api/v1/workspaces')
  }

  async createWorkspace(): Promise<ApiResponse> {
    return this.post('/api/v1/workspaces', {})
  }

  // Billing API
  async getBillingLimits(workspaceId: string): Promise<ApiResponse<BillingLimitsResponse>> {
    return this.get(`/api/v1/billing/limits?workspace_id=${workspaceId}`)
  }

  async createCheckoutSession(workspaceId: string, plan: string): Promise<ApiResponse<CheckoutSessionResponse>> {
    return this.post('/api/v1/billing/checkout-session', { workspace_id: workspaceId, plan })
  }

  async getCustomerPortal(workspaceId: string): Promise<ApiResponse<BillingPortalResponse>> {
    return this.get(`/api/v1/billing/portal?workspace_id=${workspaceId}`)
  }

  // Team Management API
  async getWorkspaceMembers(workspaceId: string): Promise<ApiResponse<TeamMemberResponse[]>> {
    return this.get(`/api/v1/workspaces/${workspaceId}/members`)
  }

  async inviteWorkspaceMember(workspaceId: string, email: string, role: string): Promise<ApiResponse<TeamMemberResponse>> {
    return this.post(`/api/v1/workspaces/${workspaceId}/members/invite`, { email, role })
  }

  async updateMemberRole(workspaceId: string, memberId: string, role: string): Promise<ApiResponse<TeamMemberResponse>> {
    return this.patch(`/api/v1/workspaces/${workspaceId}/members/${memberId}`, { role })
  }

  async removeWorkspaceMember(workspaceId: string, memberId: string): Promise<ApiResponse> {
    return this.delete(`/api/v1/workspaces/${workspaceId}/members/${memberId}`)
  }

  // User Profile API
  async updateUserProfile(data: { first_name?: string; last_name?: string; timezone?: string }): Promise<ApiResponse> {
    return this.put('/api/v1/users/me', data)
  }

  // Settings API
  async getWorkspaceSettings(workspaceId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/settings/workspace/${workspaceId}`)
  }

  async updateWorkspaceSettings(workspaceId: string, settings: { openai_api_key?: string }): Promise<ApiResponse> {
    return this.patch(`/api/v1/settings/workspace/${workspaceId}`, settings)
  }

  // Playbooks API
  async listPlaybooks(workspaceId?: string): Promise<ApiResponse> {
    const url = workspaceId 
      ? `/api/v1/playbooks?workspace_id=${workspaceId}`
      : '/api/v1/playbooks'
    return this.get(url)
  }

  async getPlaybook(playbookId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/playbooks/${playbookId}`)
  }

  async getPlaybookYaml(playbookId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/playbooks/${playbookId}/yaml`)
  }

  // Optimizer Recommendations API
  async applyRecommendation(productId: string, action: string, config: Record<string, any> = {}): Promise<ApiResponse> {
    return this.post(`/api/v1/products/${productId}/apply-recommendation`, {
      action,
      recommendation_config: config
    })
  }

  // Custom Playbooks API
  async listCustomPlaybooks(workspaceId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/playbooks/custom?workspace_id=${workspaceId}`)
  }

  async getCustomPlaybook(playbookId: string, workspaceId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/playbooks/custom/${playbookId}?workspace_id=${workspaceId}`)
  }

  async createCustomPlaybook(workspaceId: string, data: {
    name: string
    playbook_id: string
    description?: string
    yaml_content: string
    base_playbook_id?: string
  }): Promise<ApiResponse> {
    return this.post(`/api/v1/playbooks/custom?workspace_id=${workspaceId}`, data)
  }

  async updateCustomPlaybook(playbookId: string, workspaceId: string, data: {
    name?: string
    description?: string
    yaml_content?: string
  }): Promise<ApiResponse> {
    return this.patch(`/api/v1/playbooks/custom/${playbookId}?workspace_id=${workspaceId}`, data)
  }

  async deleteCustomPlaybook(playbookId: string, workspaceId: string): Promise<ApiResponse> {
    return this.delete(`/api/v1/playbooks/custom/${playbookId}?workspace_id=${workspaceId}`)
  }

  // Playground API
  async getPlaygroundStatus(productId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/playground/status/${productId}`)
  }

  async queryPlayground(productId: string, query: string, topK: number = 5, useVersion: 'current' | 'prod' = 'current'): Promise<ApiResponse> {
    return this.post('/api/v1/playground/query', {
      product_id: productId,
      query: query,
      top_k: topK,
      use: useVersion
    })
  }

  // Chunk Metadata API
  async getChunkMetadata(
    productId: string,
    params?: {
      version?: number
      section?: string
      field_name?: string
      limit?: number
      offset?: number
    }
  ): Promise<ApiResponse> {
    const queryParams = new URLSearchParams()
    if (params?.version !== undefined) {
      queryParams.append('version', params.version.toString())
    }
    if (params?.section) {
      queryParams.append('section', params.section)
    }
    if (params?.field_name) {
      queryParams.append('field_name', params.field_name)
    }
    if (params?.limit !== undefined) {
      queryParams.append('limit', params.limit.toString())
    }
    if (params?.offset !== undefined) {
      queryParams.append('offset', params.offset.toString())
    }
    
    const queryString = queryParams.toString()
    const url = `/api/v1/products/${productId}/chunk-metadata${queryString ? `?${queryString}` : ''}`
    return this.get(url)
  }

  // Embedding Models API
  async getEmbeddingModels(params?: {
    model_type?: string
    free_only?: boolean
    paid_only?: boolean
  }): Promise<ApiResponse> {
    const queryParams = new URLSearchParams()
    if (params?.model_type) {
      queryParams.append('model_type', params.model_type)
    }
    if (params?.free_only !== undefined) {
      queryParams.append('free_only', params.free_only.toString())
    }
    if (params?.paid_only !== undefined) {
      queryParams.append('paid_only', params.paid_only.toString())
    }
    
    const queryString = queryParams.toString()
    const url = `/api/v1/embedding-models${queryString ? `?${queryString}` : ''}`
    return this.get(url)
  }

  async getEmbeddingModel(modelId: string): Promise<ApiResponse> {
    return this.get(`/api/v1/embedding-models/${modelId}`)
  }

  // AI Readiness API
  async assessAIReadiness(productId: string, useVersion: 'current' | 'prod' = 'current'): Promise<ApiResponse> {
    return this.post(`/api/v1/products/${productId}/assess-ai-readiness`, {
      use: useVersion
    })
  }

  async improveAIReadiness(productId: string, config: Record<string, any>): Promise<ApiResponse> {
    return this.post(`/api/v1/products/${productId}/improve-ai-readiness`, config)
  }

  // MLflow Metrics API (deprecated/disabled but kept for compatibility)
  async getMLflowMetricsForVersion(productId: string, version: number): Promise<ApiResponse> {
    // MLflow integration is disabled, return empty response
    return Promise.resolve({
      data: null,
      error: 'MLflow integration is disabled'
    })
  }

  // ACL API
  async listACLs(params: { product_id?: string }): Promise<ApiResponse> {
    const queryParams = new URLSearchParams()
    if (params.product_id) {
      queryParams.append('product_id', params.product_id)
    }
    const queryString = queryParams.toString()
    return this.get(`/api/v1/acls${queryString ? `?${queryString}` : ''}`)
  }

  async createACL(data: {
    product_id: string
    user_id: string
    access_type: string
    index_scope?: string
    doc_scope?: string
    field_scope?: string
  }): Promise<ApiResponse> {
    return this.post('/api/v1/acls', data)
  }

  async deleteACL(aclId: string): Promise<ApiResponse> {
    return this.delete(`/api/v1/acls/${aclId}`)
  }

  async deleteACLs(params: { acl_id: string }): Promise<ApiResponse> {
    return this.delete(`/api/v1/acls/${params.acl_id}`)
  }

  // Cost Estimation API
  async estimateCost(file: File, playbookId?: string): Promise<ApiResponse> {
    const formData = new FormData()
    formData.append('file', file)
    if (playbookId) {
      formData.append('playbook_id', playbookId)
    }
    
    // Use fetch directly since we need FormData
    try {
      const url = `${this.baseUrl}/api/v1/cost/estimate`
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      })
      
      const status = response.status
      if (!response.ok) {
        const errorText = await response.text()
        return {
          error: `Request failed: ${errorText}`,
          status,
        }
      }
      
      const data = await response.json()
      return { data, status }
    } catch (error) {
      console.error('API request failed:', error)
      return {
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      }
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient()

