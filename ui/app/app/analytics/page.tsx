'use client'

import { useState, useEffect } from 'react'
import { 
  BarChart3, 
  TrendingUp, 
  Activity, 
  Users, 
  Database, 
  Zap, 
  Clock,
  CheckCircle,
  AlertTriangle,
  ArrowUp,
  ArrowDown
} from 'lucide-react'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient } from '@/lib/api-client'
import { useSession } from 'next-auth/react'

interface AnalyticsData {
  totalProducts: number
  totalDataSources: number
  totalPipelineRuns: number
  successRate: number
  avgProcessingTime: number
  dataQualityScore: number
  recentActivity: Array<{
    id: string
    type: string
    message: string
    timestamp: string
    status: 'success' | 'warning' | 'error'
  }>
  monthlyStats: Array<{
    month: string
    pipelineRuns: number
    dataProcessed: number
    qualityScore: number
  }>
}

export default function AnalyticsPage() {
  const { data: session } = useSession()
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAnalytics()
  }, [])

  const loadAnalytics = async () => {
    try {
      setLoading(true)
      // Get workspace ID from session or use default for testing
      const workspaceId = session?.user?.workspace_ids?.[0] || '550e8400-e29b-41d4-a716-446655440001'
      
      const response = await apiClient.get(`/api/v1/analytics/metrics?workspace_id=${workspaceId}`)
      const data = response.data
      
      // Transform snake_case to camelCase
      setAnalytics({
        totalProducts: data.total_products || 0,
        totalDataSources: data.total_data_sources || 0,
        totalPipelineRuns: data.total_pipeline_runs || 0,
        successRate: data.success_rate || 0,
        avgProcessingTime: data.avg_processing_time || 0,
        dataQualityScore: data.data_quality_score || 0,
        recentActivity: data.recent_activity || [],
        monthlyStats: data.monthly_stats || []
      })
    } catch (err) {
      console.error('Failed to load analytics:', err)
      // Fallback to mock data if API fails
      const mockData: AnalyticsData = {
        totalProducts: 0,
        totalDataSources: 0,
        totalPipelineRuns: 0,
        successRate: 0,
        avgProcessingTime: 0,
        dataQualityScore: 0,
        recentActivity: [],
        monthlyStats: []
      }
      setAnalytics(mockData)
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-500" />
      default:
        return <Activity className="h-4 w-4 text-gray-500" />
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="text-gray-600 mt-2">Monitor your data pipeline performance and insights</p>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Database className="h-8 w-8 text-blue-500" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Products</p>
                <p className="text-2xl font-semibold text-gray-900">{analytics?.totalProducts || 0}</p>
              </div>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <BarChart3 className="h-8 w-8 text-green-500" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Data Sources</p>
                <p className="text-2xl font-semibold text-gray-900">{analytics?.totalDataSources || 0}</p>
              </div>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Zap className="h-8 w-8 text-purple-500" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Pipeline Runs</p>
                <p className="text-2xl font-semibold text-gray-900">{analytics?.totalPipelineRuns || 0}</p>
              </div>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <TrendingUp className="h-8 w-8 text-orange-500" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Success Rate</p>
                <p className="text-2xl font-semibold text-gray-900">{analytics?.successRate || 0}%</p>
              </div>
            </div>
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Overview</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Average Processing Time</span>
                <span className="text-sm font-medium text-gray-900">{analytics?.avgProcessingTime || 0} minutes</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Data Quality Score</span>
                <div className="flex items-center">
                  <span className="text-sm font-medium text-gray-900 mr-2">{analytics?.dataQualityScore || 0}%</span>
                  <ArrowUp className="h-4 w-4 text-green-500" />
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Monthly Trends</h3>
            <div className="space-y-3">
              {analytics?.monthlyStats?.slice(-3).map((stat, index) => (
                <div key={stat.month} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{stat.month}</span>
                  <div className="flex items-center space-x-4">
                    <span className="text-xs text-gray-500">{stat.pipelineRuns} runs</span>
                    <span className="text-xs text-gray-500">{stat.dataProcessed}TB</span>
                    <span className="text-xs text-gray-500">{stat.qualityScore}%</span>
                  </div>
                </div>
              )) || (
                <div className="text-sm text-gray-500">No monthly data available</div>
              )}
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Recent Activity</h3>
          </div>
          <div className="divide-y divide-gray-200">
            {analytics?.recentActivity?.map((activity) => (
              <div key={activity.id} className="px-6 py-4">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    {getStatusIcon(activity.status)}
                  </div>
                  <div className="ml-3 flex-1">
                    <p className="text-sm text-gray-900">{activity.message}</p>
                    <p className="text-xs text-gray-500 mt-1">{formatTimestamp(activity.timestamp)}</p>
                  </div>
                </div>
              </div>
            )) || (
              <div className="px-6 py-4">
                <div className="text-sm text-gray-500">No recent activity</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
