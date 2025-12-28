'use client'

import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertTriangle, Loader2, AlertCircle, Lightbulb, BookOpen, TrendingUp, Sparkles } from 'lucide-react'
import { apiClient, ProductInsightsResponse } from '@/lib/api-client'
import { useToast } from './ui/toast'
import { Button } from '@/components/ui/button'

interface AITrustScoreDisplayProps {
  productId: string
  showTitle?: boolean
}

const METRIC_NAMES: Record<string, string> = {
  AI_Trust_Score: 'AI Trust Score',
  Completeness: 'Completeness',
  Accuracy: 'Accuracy',
  Secure: 'Security',
  Quality: 'Quality',
  Timeliness: 'Timeliness',
  Token_Count: 'Token Count',
  GPT_Confidence: 'GPT Confidence',
  Context_Quality: 'Context Quality',
  Metadata_Presence: 'Metadata Presence',
  Audience_Intentionality: 'Audience Intentionality',
  Diversity: 'Diversity',
  Audience_Accessibility: 'Audience Accessibility',
  KnowledgeBase_Ready: 'Knowledge Base Ready',
}

const METRIC_DESCRIPTIONS: Record<string, string> = {
  Completeness: 'How complete the content is',
  Accuracy: 'Accuracy of the information',
  Secure: 'Security and privacy compliance',
  Quality: 'Overall content quality',
  Timeliness: 'How current/timely the content is',
  Token_Count: 'Normalized token count',
  GPT_Confidence: 'Confidence level for GPT processing',
  Context_Quality: 'Quality of context provided',
  Metadata_Presence: 'How much metadata is present',
  Audience_Intentionality: 'How well content targets its audience',
  Diversity: 'Content diversity/variety',
  Audience_Accessibility: 'How accessible content is to audience',
  KnowledgeBase_Ready: 'Ready for knowledge base use',
}

export function AITrustScoreDisplay({ productId, showTitle = true }: AITrustScoreDisplayProps) {
  const [insights, setInsights] = useState<ProductInsightsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [applyingRecommendation, setApplyingRecommendation] = useState<string | null>(null)
  const { addToast } = useToast()

  useEffect(() => {
    loadInsights()
  }, [productId])

  const loadInsights = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.getProductInsights(productId)
      if (response.error) {
        setError(response.error)
        addToast({
          type: 'error',
          message: `Failed to load AI Trust Score: ${response.error}`,
        })
      } else if (response.data) {
        setInsights(response.data)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load AI Trust Score'
      setError(errorMessage)
      addToast({
        type: 'error',
        message: errorMessage,
      })
    } finally {
      setLoading(false)
    }
  }

  const getActionLabel = (action: string): string => {
    switch (action) {
      case 'increase_chunk_overlap':
        return 'Increase Overlap'
      case 'switch_playbook':
        return 'Switch Playbook'
      case 'enhance_normalization':
        return 'Enhance Normalization'
      case 'extract_metadata':
        return 'Extract Metadata'
      case 'apply_all_recommendations':
        return 'Apply All'
      default:
        return 'Apply'
    }
  }

  const handleApplyRecommendation = async (recommendation: any, index: number) => {
    const recommendationKey = `${recommendation.type}-${index}`
    setApplyingRecommendation(recommendationKey)
    
    try {
      const response = await apiClient.applyRecommendation(
        productId,
        recommendation.action,
        recommendation.config || {}
      )
      
      if (response.error) {
        addToast({
          type: 'error',
          message: `Failed to apply recommendation: ${response.error}`,
        })
      } else if (response.data) {
        const result = response.data
        addToast({
          type: 'success',
          message: result.message || 'Recommendation applied successfully!',
        })
        
        // Reload insights to show updated recommendations
        setTimeout(() => {
          loadInsights()
        }, 1000)
        
        // Show message about pipeline rerun if needed
        if (result.requires_pipeline_rerun) {
          setTimeout(() => {
            addToast({
              type: 'info',
              message: 'Please re-run the pipeline to see the full effects of this change.',
            })
          }, 2000)
        }
      }
    } catch (err) {
      addToast({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to apply recommendation',
      })
    } finally {
      setApplyingRecommendation(null)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 bg-green-50'
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-50'
    return 'text-red-600 bg-red-50'
  }

  const getScoreIcon = (score: number) => {
    if (score >= 0.8) return <CheckCircle className="h-5 w-5 text-green-600" />
    if (score >= 0.6) return <AlertTriangle className="h-5 w-5 text-yellow-600" />
    return <XCircle className="h-5 w-5 text-red-600" />
  }

  const getPolicyStatusColor = (status: string) => {
    switch (status) {
      case 'passed':
        return 'bg-green-50 border-green-200 text-green-800'
      case 'failed':
        return 'bg-red-50 border-red-200 text-red-800'
      case 'warnings':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800'
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800'
    }
  }

  const getPolicyStatusIcon = (status: string) => {
    switch (status) {
      case 'passed':
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-600" />
      case 'warnings':
        return <AlertTriangle className="h-5 w-5 text-yellow-600" />
      default:
        return <AlertCircle className="h-5 w-5 text-gray-600" />
    }
  }

  const formatMetricValue = (key: string, value: number) => {
    // Token count: show as integer with separators (never as percentage)
    if (key === 'Token_Count') {
      return Math.round(value).toLocaleString()
    }

    // All other metrics are percentage-like (scores, quality, readiness, confidence, etc.)
    // Backend returns metrics in 0-100 scale, but some might be in 0-1 or >100
    // Normalize to 0-100 scale for display:
    let normalized = value
    
    // Handle different input scales
    if (normalized > 100) {
      // Values > 100: likely incorrectly scaled (e.g., 7500 means 75.0)
      // Divide by 100 to get back to 0-100 scale
      normalized = normalized / 100
    } else if (normalized <= 1 && normalized >= 0) {
      // Values 0-1: convert to percentage (multiply by 100)
      normalized = normalized * 100
    }
    // Values 1-100: use as-is (already in correct scale)
    
    // Ensure normalized is between 0-100
    normalized = Math.max(0, Math.min(100, normalized))
    
    return `${normalized.toFixed(2)}%`
  }

  // Helper to get normalized value for progress bar (0-1 scale)
  const getNormalizedValueForProgress = (key: string, value: number): number => {
    if (key === 'Token_Count') {
      // Token count: normalize to 0-1 based on reasonable max (e.g., 1000 tokens = 100%)
      return Math.min(value / 1000, 1.0)
    }
    
    // Normalize percentage metrics to 0-1 for progress bar
    let normalized = value
    if (normalized > 100) {
      normalized = normalized / 100
    } else if (normalized <= 1 && normalized >= 0) {
      normalized = normalized * 100
    }
    normalized = Math.max(0, Math.min(100, normalized))
    return normalized / 100  // Convert to 0-1 for progress bar
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {showTitle && <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Trust Score</h2>}
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 text-gray-400 animate-spin mr-2" />
          <p className="text-gray-600">Loading AI Trust Score...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {showTitle && <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Trust Score</h2>}
        <div className="flex items-center justify-center py-8">
          <AlertCircle className="h-6 w-6 text-red-500 mr-2" />
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    )
  }

  if (!insights) {
    return null
  }

  const { fingerprint, policy, optimizer } = insights
  
  // Extract and normalize AI Trust Score (handle both 0-1 and 0-100 formats)
  let trustScore = 0
  if (fingerprint?.AI_Trust_Score !== undefined) {
    const rawScore = typeof fingerprint.AI_Trust_Score === 'number' 
      ? fingerprint.AI_Trust_Score 
      : parseFloat(fingerprint.AI_Trust_Score as any) || 0
    trustScore = rawScore > 1 ? rawScore / 100 : rawScore
  }

  // Get all metrics except AI_Trust_Score, GPT_Confidence, and page for detailed breakdown
  const otherMetrics = Object.entries(fingerprint || {})
    .filter(([key]) => key !== 'AI_Trust_Score' && key !== 'GPT_Confidence' && key !== 'page')
    .sort(([a], [b]) => {
      // Priority order for important metrics
      const order = ['Secure', 'Metadata_Presence', 'KnowledgeBase_Ready', 'Quality', 'Completeness']
      const aIdx = order.indexOf(a)
      const bIdx = order.indexOf(b)
      if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx
      if (aIdx !== -1) return -1
      if (bIdx !== -1) return 1
      return a.localeCompare(b)
    })

  return (
    <div className="space-y-6">
      {showTitle && <h2 className="text-lg font-semibold text-gray-900">AI Trust Score</h2>}

      {/* Overall AI Trust Score */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className={`rounded-lg p-6 ${getScoreColor(trustScore)}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium mb-1">Overall AI Trust Score</p>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold">{(trustScore * 100).toFixed(1)}%</span>
                <span className="text-sm opacity-75">/ 100%</span>
              </div>
              <p className="text-xs mt-2 opacity-75">
                {trustScore >= 0.8
                  ? 'Excellent - Ready for AI use'
                  : trustScore >= 0.6
                  ? 'Good - Minor improvements recommended'
                  : 'Needs Improvement - Significant enhancements required'}
              </p>
            </div>
            <div className="flex-shrink-0">{getScoreIcon(trustScore)}</div>
          </div>
        </div>
      </div>

      {/* Policy Status Banner */}
      <div className={`rounded-lg border p-4 ${getPolicyStatusColor(policy.status || 'unknown')}`}>
        <div className="flex items-start gap-3">
          {getPolicyStatusIcon(policy.status || 'unknown')}
          <div className="flex-1">
            <h3 className="font-medium mb-1">
              Policy Evaluation: {policy.status ? (policy.status.charAt(0).toUpperCase() + policy.status.slice(1)) : 'Unknown'}
            </h3>
            {policy.violations && policy.violations.length > 0 && (
              <div className="mt-2">
                <p className="text-sm font-medium mb-1">Violations:</p>
                <ul className="list-disc list-inside text-sm space-y-1">
                  {(policy.violations || []).map((violation: string, idx: number) => (
                    <li key={idx}>{violation}</li>
                  ))}
                </ul>
              </div>
            )}
            {policy.warnings && policy.warnings.length > 0 && (
              <div className="mt-2">
                <p className="text-sm font-medium mb-1">Warnings:</p>
                <ul className="list-disc list-inside text-sm space-y-1">
                  {(policy.warnings || []).map((warning: string, idx: number) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detailed Metrics Breakdown */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-sm font-medium text-gray-900 mb-4 flex items-center gap-2">
          <BookOpen className="h-5 w-5" />
          Detailed Metrics
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {otherMetrics.map(([key, value]) => {
            const displayName = METRIC_NAMES[key] || key.replace(/_/g, ' ')
            const description = METRIC_DESCRIPTIONS[key] || ''
            const numericValue = typeof value === 'number' ? value : parseFloat(value as any) || 0
            
            // Normalize value for color determination and progress bar (0-1 scale)
            const normalizedForColor = getNormalizedValueForProgress(key, numericValue)
            const scoreColor = normalizedForColor >= 0.8 ? 'text-green-600' : normalizedForColor >= 0.6 ? 'text-yellow-600' : 'text-red-600'
            
            return (
              <div key={key} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h4 className="text-sm font-medium text-gray-900">{displayName}</h4>
                    {description && (
                      <p className="text-xs text-gray-500 mt-1">{description}</p>
                    )}
                  </div>
                  <div className={`text-lg font-semibold ${scoreColor} ml-2`}>
                    {formatMetricValue(key, numericValue)}
                  </div>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      normalizedForColor >= 0.8 ? 'bg-green-500' : normalizedForColor >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${Math.min(normalizedForColor * 100, 100)}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Optimizer Suggestions */}
      {optimizer && (optimizer.suggestions || optimizer.playbook_recommendations || (optimizer.actionable_recommendations && optimizer.actionable_recommendations.length > 0)) && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-md font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-yellow-600" />
            Optimization Suggestions
          </h3>
          
          {/* Actionable Recommendations */}
          {optimizer.actionable_recommendations && optimizer.actionable_recommendations.length > 0 && (
            <div className="mb-6">
              <p className="text-sm font-medium text-gray-700 mb-3">Recommendations:</p>
              <div className="space-y-3">
                {optimizer.actionable_recommendations.map((rec: any, idx: number) => {
                  const isApplying = applyingRecommendation === `${rec.type}-${idx}`
                  const actionLabel = getActionLabel(rec.action)
                  
                  return (
                    <div key={idx} className="border border-gray-200 rounded-lg p-4 bg-gray-50 hover:bg-gray-100 transition-colors">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Sparkles className="h-4 w-4 text-blue-600" />
                            <p className="text-sm text-gray-700">{rec.message}</p>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          className="flex-shrink-0"
                          onClick={() => handleApplyRecommendation(rec, idx)}
                          disabled={isApplying}
                        >
                          {isApplying ? (
                            <>
                              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                              Applying...
                            </>
                          ) : (
                            <>
                              <Sparkles className="h-3 w-3 mr-1" />
                              {actionLabel}
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
          
          {/* General Suggestions (non-actionable) */}
          {optimizer.suggestions && optimizer.suggestions.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700 mb-2">General Suggestions:</p>
              <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                {(optimizer.suggestions || []).map((suggestion: string, idx: number) => (
                  <li key={idx}>{suggestion}</li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Playbook Recommendations */}
          {optimizer.playbook_recommendations && optimizer.playbook_recommendations.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Playbook Recommendations:</p>
              <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                {(optimizer.playbook_recommendations || []).map((rec: string, idx: number) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

