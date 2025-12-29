'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { Package, Database, TrendingUp, Activity, AlertCircle, CheckCircle, Clock, Plus, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/status-badge'
import { StatCardSkeleton, ListSkeleton, CardSkeleton } from '@/components/ui/skeleton'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient } from '@/lib/api-client'
import { exchangeToken } from '@/lib/auth-utils'

interface Product {
  id: string
  name: string
  status: 'draft' | 'running' | 'ready' | 'failed'
  created_at: string
}

interface DataSource {
  id: string
  type: string
  created_at: string
}

export default function DashboardPage() {
  const { data: session, status } = useSession()
  const [products, setProducts] = useState<Product[]>([])
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    totalProducts: 0,
    totalDataSources: 0,
    runningProducts: 0,
    failedProducts: 0,
    readyProducts: 0,
    draftProducts: 0
  })

  // Exchange token when authenticated (ensures user is registered in backend)
  useEffect(() => {
    if (status === 'authenticated' && session) {
      exchangeToken().catch((error) => {
        console.error("Token exchange failed on dashboard:", error)
      })
      // Load data when authenticated
      loadDashboardData()
    }
  }, [status, session])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      
      // Load products
      const productsResponse = await apiClient.getProducts()
      if (productsResponse.data) {
        const productsData = productsResponse.data as Product[]
        setProducts(productsData)
        
        // Calculate stats
        const stats = {
          totalProducts: productsData.length,
          totalDataSources: 0, // Will be calculated from data sources
          runningProducts: productsData.filter(p => p.status === 'running').length,
          failedProducts: productsData.filter(p => p.status === 'failed').length,
          readyProducts: productsData.filter(p => p.status === 'ready').length,
          draftProducts: productsData.filter(p => p.status === 'draft').length
        }
        setStats(stats)
      }

      // Load data sources (we'll need to get this from all products)
      // For now, we'll estimate based on products
      setStats(prev => ({
        ...prev,
        totalDataSources: products.length * 2 // Rough estimate
      }))
      
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Status helpers removed - using StatusBadge component instead

  if (loading) {
    return (
      <AppLayout>
        <div className="p-6 bg-gradient-to-br from-gray-50 via-blue-50/30 to-indigo-50/30 min-h-screen">
          <div className="mb-8">
            <div className="h-10 bg-gray-200 rounded-xl w-1/4 mb-2 animate-pulse"></div>
            <div className="h-6 bg-gray-200 rounded w-1/3 animate-pulse"></div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {[...Array(4)].map((_, i) => (
              <StatCardSkeleton key={i} />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <CardSkeleton />
            <CardSkeleton />
          </div>
          <CardSkeleton />
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="p-6 bg-gradient-to-br from-gray-50 via-blue-50/30 to-indigo-50/30 min-h-screen">
        {/* Welcome Section */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2 tracking-tight">Dashboard</h1>
          <p className="text-lg text-gray-600">
            Welcome back! Here's an overview of your data products and sources.
          </p>
        </div>

        {/* Enhanced Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-xl shadow-md border border-gray-100 hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-3 mr-4 shadow-sm">
                  <Package className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600 mb-1">Total Products</p>
                  <p className="text-3xl font-bold text-gray-900">{stats.totalProducts}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-md border border-gray-100 hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl p-3 mr-4 shadow-sm">
                  <Database className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600 mb-1">Data Sources</p>
                  <p className="text-3xl font-bold text-gray-900">{stats.totalDataSources}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-md border border-gray-100 hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl p-3 mr-4 shadow-sm">
                  <CheckCircle className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600 mb-1">Ready Products</p>
                  <p className="text-3xl font-bold text-gray-900">{stats.readyProducts}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-md border border-gray-100 hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-3 mr-4 shadow-sm">
                  <Activity className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600 mb-1">Running</p>
                  <p className="text-3xl font-bold text-gray-900">{stats.runningProducts}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Status Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-white p-6 rounded-xl shadow-md border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Product Status Overview</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-100">
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full mr-3 shadow-sm"></div>
                  <span className="text-sm font-medium text-gray-700">Ready</span>
                </div>
                <span className="text-lg font-bold text-gray-900">{stats.readyProducts}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-100">
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full mr-3 shadow-sm animate-pulse"></div>
                  <span className="text-sm font-medium text-gray-700">Running</span>
                </div>
                <span className="text-lg font-bold text-gray-900">{stats.runningProducts}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-gradient-to-r from-gray-500 to-slate-600 rounded-full mr-3 shadow-sm"></div>
                  <span className="text-sm font-medium text-gray-700">Draft</span>
                </div>
                <span className="text-lg font-bold text-gray-900">{stats.draftProducts}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-100">
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-gradient-to-r from-red-500 to-rose-600 rounded-full mr-3 shadow-sm"></div>
                  <span className="text-sm font-medium text-gray-700">Failed</span>
                </div>
                <span className="text-lg font-bold text-gray-900">{stats.failedProducts}</span>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-md border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Quick Actions</h3>
            <div className="space-y-3">
              <Link href="/app/products/new">
                <Button className="w-full justify-start bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-md hover:shadow-lg transition-all">
                  <Plus className="h-4 w-4 mr-2" />
                  Create New Product
                </Button>
              </Link>
              <Link href="/app/products">
                <Button variant="outline" className="w-full justify-start border-2 hover:border-blue-300 hover:bg-blue-50 transition-all">
                  <Package className="h-4 w-4 mr-2" />
                  Manage Products
                </Button>
              </Link>
              <Link href="/app/datasources">
                <Button variant="outline" className="w-full justify-start border-2 hover:border-blue-300 hover:bg-blue-50 transition-all">
                  <Database className="h-4 w-4 mr-2" />
                  Manage Data Sources
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Recent Products */}
        <div className="bg-white rounded-xl shadow-md border border-gray-100">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Recent Products</h3>
              <Link href="/app/products">
                <Button variant="outline" size="sm" className="border-2 hover:border-blue-300 hover:bg-blue-50">
                  View All
                </Button>
              </Link>
            </div>
          </div>
          <div className="p-6">
            {products.length === 0 ? (
              <div className="text-center py-12">
                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-4">
                  <Package className="h-10 w-10 text-blue-600" />
                </div>
                <h4 className="text-xl font-semibold text-gray-900 mb-2">No products yet</h4>
                <p className="text-gray-600 mb-6 max-w-md mx-auto">Get started by creating your first data product to begin processing and analyzing your data.</p>
                <Link href="/app/products/new">
                  <Button className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-md hover:shadow-lg">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Product
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {products.slice(0, 5).map((product) => {
                  return (
                    <Link 
                      key={product.id} 
                      href={`/app/products/${product.id}`}
                      className="block group"
                    >
                      <div className="flex items-center justify-between p-4 border-2 border-gray-200 rounded-xl hover:border-blue-300 hover:bg-blue-50/50 transition-all duration-200 cursor-pointer group-hover:shadow-md">
                        <div className="flex items-center">
                          <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-2.5 mr-4 shadow-sm group-hover:scale-110 transition-transform">
                            <Package className="h-5 w-5 text-white" />
                          </div>
                          <div>
                            <h4 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors mb-1">{product.name}</h4>
                            <p className="text-sm text-gray-500">
                              Created {new Date(product.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center">
                          <StatusBadge status={product.status as any} />
                        </div>
                      </div>
                    </Link>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}