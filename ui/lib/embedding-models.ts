/**
 * Embedding model configuration for frontend.
 * 
 * This module provides utilities for working with embedding models,
 * including getting available options, dimensions, and API key requirements.
 * Models are fetched from the backend API to ensure consistency.
 */

import { apiClient } from './api-client'

export interface EmbeddingModelOption {
  value: string
  label: string
}

export interface EmbeddingModel {
  id: string
  name: string
  description: string
  dimension: number
  requires_api_key: boolean
  cost_per_token?: number
  metadata?: Record<string, any>
}

/**
 * Fallback embedding model configurations (used if API fails).
 * These match the original hardcoded models for backward compatibility.
 */
const FALLBACK_EMBEDDING_MODELS: Record<string, { name: string; dimension: number; requiresApiKey: boolean; description: string }> = {
  minilm: {
    name: 'MiniLM',
    dimension: 384,
    requiresApiKey: false,
    description: 'Lightweight sentence transformer model optimized for speed'
  },
  'minilm-l12': {
    name: 'MiniLM-L12',
    dimension: 384,
    requiresApiKey: false,
    description: 'Higher quality MiniLM model with 12 layers'
  },
  mpnet: {
    name: 'MPNet',
    dimension: 768,
    requiresApiKey: false,
    description: "Microsoft's MPNet model for high-quality embeddings"
  },
  'openai-ada-002': {
    name: 'OpenAI Ada-002',
    dimension: 1536,
    requiresApiKey: true,
    description: "OpenAI's text-embedding-ada-002 model"
  },
  'openai-3-small': {
    name: 'OpenAI Text-3-Small',
    dimension: 1536,
    requiresApiKey: true,
    description: "OpenAI's latest small embedding model"
  },
  'openai-3-large': {
    name: 'OpenAI Text-3-Large',
    dimension: 3072,
    requiresApiKey: true,
    description: "OpenAI's latest large embedding model with higher dimensions"
  }
}

// Cache for embedding models fetched from API
let embeddingModelsCache: EmbeddingModel[] | null = null
let embeddingModelsCacheTime: number = 0
const CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

/**
 * Fetch embedding models from the API.
 * 
 * @param useCache - Whether to use cached models if available
 * @returns Array of embedding models
 */
async function fetchEmbeddingModels(useCache: boolean = true): Promise<EmbeddingModel[]> {
  // Check cache first
  if (useCache && embeddingModelsCache && (Date.now() - embeddingModelsCacheTime) < CACHE_DURATION) {
    return embeddingModelsCache
  }

  try {
    const response = await apiClient.getEmbeddingModels({ free_only: false })
    
    if (response.error || !response.data) {
      console.warn('Failed to fetch embedding models from API, using fallback:', response.error)
      // Return fallback models
      return Object.entries(FALLBACK_EMBEDDING_MODELS).map(([id, config]) => ({
        id,
        name: config.name,
        description: config.description,
        dimension: config.dimension,
        requires_api_key: config.requiresApiKey
      }))
    }

    // Cache the results
    embeddingModelsCache = response.data.models || []
    embeddingModelsCacheTime = Date.now()
    
    return embeddingModelsCache || []
  } catch (error) {
    console.error('Error fetching embedding models:', error)
    // Return fallback models on error
    return Object.entries(FALLBACK_EMBEDDING_MODELS).map(([id, config]) => ({
      id,
      name: config.name,
      description: config.description,
      dimension: config.dimension,
      requires_api_key: config.requiresApiKey
    }))
  }
}

/**
 * Get list of embedding model options for select dropdowns.
 * 
 * @param useCache - Whether to use cached models if available
 * @returns Array of embedding model options with value and label
 */
export async function getEmbeddingModelOptions(useCache: boolean = true): Promise<EmbeddingModelOption[]> {
  const models = await fetchEmbeddingModels(useCache)
  return models.map((model) => ({
    value: model.id,
    label: model.name
  }))
}

/**
 * Synchronous version that uses cache or fallback.
 * Use this for immediate access, but prefer async version for fresh data.
 */
export function getEmbeddingModelOptionsSync(): EmbeddingModelOption[] {
  if (embeddingModelsCache) {
    return embeddingModelsCache.map((model) => ({
      value: model.id,
      label: model.name
    }))
  }
  
  // Use fallback if cache not available
  return Object.entries(FALLBACK_EMBEDDING_MODELS).map(([value, config]) => ({
    value,
    label: config.name
  }))
}

/**
 * Get the embedding dimension for a given model name.
 * 
 * @param modelName - The embedding model identifier
 * @returns The dimension of the embedding model, or undefined if model not found
 */
export async function getEmbeddingDimension(modelName: string): Promise<number | undefined> {
  // Check cache first
  if (embeddingModelsCache) {
    const model = embeddingModelsCache.find(m => m.id === modelName)
    if (model) return model.dimension
  }
  
  // Check fallback
  const fallbackModel = FALLBACK_EMBEDDING_MODELS[modelName]
  if (fallbackModel) return fallbackModel.dimension
  
  // Try to fetch from API
  try {
    const models = await fetchEmbeddingModels(false)
    const model = models.find(m => m.id === modelName)
    if (model) return model.dimension
  } catch (error) {
    console.error('Error fetching embedding dimension:', error)
  }
  
  // Return undefined if model not found anywhere
  return undefined
}

/**
 * Synchronous version that uses cache or fallback.
 */
export function getEmbeddingDimensionSync(modelName: string): number | undefined {
  if (embeddingModelsCache) {
    const model = embeddingModelsCache.find(m => m.id === modelName)
    if (model) return model.dimension
  }
  
  const fallbackModel = FALLBACK_EMBEDDING_MODELS[modelName]
  return fallbackModel?.dimension
}

/**
 * Check if an embedding model requires an API key.
 * 
 * @param modelName - The embedding model identifier
 * @returns True if the model requires an API key, false otherwise
 */
export async function requiresApiKey(modelName: string): Promise<boolean> {
  // Check cache first
  if (embeddingModelsCache) {
    const model = embeddingModelsCache.find(m => m.id === modelName)
    if (model) return model.requires_api_key
  }
  
  // Check fallback
  const fallbackModel = FALLBACK_EMBEDDING_MODELS[modelName]
  if (fallbackModel) return fallbackModel.requiresApiKey
  
  // Try to fetch from API
  try {
    const models = await fetchEmbeddingModels(false)
    const model = models.find(m => m.id === modelName)
    if (model) return model.requires_api_key || false
  } catch (error) {
    console.error('Error checking API key requirement:', error)
  }
  
  // Return false if model not found
  return false
}

/**
 * Synchronous version that uses cache or fallback.
 */
export function requiresApiKeySync(modelName: string): boolean {
  if (embeddingModelsCache) {
    const model = embeddingModelsCache.find(m => m.id === modelName)
    if (model) return model.requires_api_key
  }
  
  const fallbackModel = FALLBACK_EMBEDDING_MODELS[modelName]
  return fallbackModel?.requiresApiKey ?? false
}

/**
 * Format embedding model name for display.
 * 
 * @param modelName - The embedding model identifier
 * @returns Formatted display name for the model
 */
export function formatEmbeddingModelName(modelName: string): string {
  if (embeddingModelsCache) {
    const model = embeddingModelsCache.find(m => m.id === modelName)
    if (model) return model.name
  }
  
  const fallbackModel = FALLBACK_EMBEDDING_MODELS[modelName]
  return fallbackModel?.name || modelName
}

/**
 * Preload embedding models from API (call this on app initialization).
 * This ensures models are available immediately when needed.
 */
export async function preloadEmbeddingModels(): Promise<void> {
  try {
    await fetchEmbeddingModels(false)
  } catch (error) {
    console.error('Failed to preload embedding models:', error)
  }
}

