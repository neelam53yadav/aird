'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Plus, Database, Globe, Folder, Server, FileText, Share } from 'lucide-react'
import { Button } from '@/components/ui/button'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient } from '@/lib/api-client'

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

interface Product {
  id: string
  name: string
}

export default function DataSourcesPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/')
      return
    }

    if (status === 'authenticated') {
      loadData()
    }
  }, [status, router])

  const loadData = async () => {
    try {
      setLoading(true)
      
      // Load products first
      const productsResponse = await apiClient.getProducts()
      if (productsResponse.data) {
        setProducts(productsResponse.data as Product[])
        
        // Load data sources for each product
        const allDataSources: DataSource[] = []
        for (const product of productsResponse.data as Product[]) {
          const dataSourcesResponse = await apiClient.getDataSources(product.id)
          if (dataSourcesResponse.data) {
            allDataSources.push(...(dataSourcesResponse.data as DataSource[]))
          }
        }
        setDataSources(allDataSources)
      }
    } catch (err) {
      setError('Failed to load data sources')
    } finally {
      setLoading(false)
    }
  }

  const getDataSourceTypeIcon = (type: string) => {
    switch (type) {
      case 'web': return <Globe className="h-5 w-5 text-blue-600" />
      case 'db': return <Server className="h-5 w-5 text-green-600" />
      case 'confluence': return <FileText className="h-5 w-5 text-purple-600" />
      case 'sharepoint': return <Share className="h-5 w-5 text-orange-600" />
      case 'folder': return <Folder className="h-5 w-5 text-gray-600" />
      default: return <Database className="h-5 w-5 text-gray-600" />
    }
  }

  const getDataSourceTypeName = (type: string) => {
    switch (type) {
      case 'web': return 'Web URL'
      case 'db': return 'Database'
      case 'confluence': return 'Confluence'
      case 'sharepoint': return 'SharePoint'
      case 'folder': return 'Local Folder'
      default: return type
    }
  }

  const getProductName = (productId: string) => {
    const product = products.find(p => p.id === productId)
    return product ? product.name : 'Unknown Product'
  }

  if (status === 'loading' || loading) {
    return (
      <AppLayout>
        <div className="p-6">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="bg-white p-6 rounded-lg shadow-sm border">
                  <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/3"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </AppLayout>
    )
  }

  if (error) {
    return (
      <AppLayout>
        <div className="p-6">
          <div className="text-center py-12">
            <p className="text-red-600 mb-4">Error: {error}</p>
            <Button onClick={loadData}>Try Again</Button>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="p-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Data Sources</h1>
              <p className="text-gray-600">Manage all your data sources across products</p>
            </div>
            <div className="flex space-x-3">
              <Button variant="outline">
                <Database className="h-4 w-4 mr-2" />
                Import Data Source
              </Button>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Data Source
              </Button>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center">
              <div className="bg-blue-100 rounded-lg p-3 mr-4">
                <Database className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Total Sources</p>
                <p className="text-2xl font-bold text-gray-900">{dataSources.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center">
              <div className="bg-green-100 rounded-lg p-3 mr-4">
                <Globe className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Web Sources</p>
                <p className="text-2xl font-bold text-gray-900">
                  {dataSources.filter(ds => ds.type === 'web').length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center">
              <div className="bg-purple-100 rounded-lg p-3 mr-4">
                <Server className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Database Sources</p>
                <p className="text-2xl font-bold text-gray-900">
                  {dataSources.filter(ds => ds.type === 'db').length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center">
              <div className="bg-orange-100 rounded-lg p-3 mr-4">
                <Folder className="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">File Sources</p>
                <p className="text-2xl font-bold text-gray-900">
                  {dataSources.filter(ds => ds.type === 'folder').length}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Data Sources List */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">All Data Sources</h3>
          </div>
          <div className="p-6">
            {dataSources.length === 0 ? (
              <div className="text-center py-12">
                <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h4 className="text-lg font-medium text-gray-900 mb-2">No data sources yet</h4>
                <p className="text-gray-600 mb-6">Get started by adding your first data source to a product.</p>
                <Link href="/app/products">
                  <Button>
                    <Plus className="h-4 w-4 mr-2" />
                    Go to Products
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {dataSources.map((dataSource) => (
                  <div key={dataSource.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start mb-3">
                      <div className="bg-gray-100 rounded-lg p-2 mr-3 flex-shrink-0">
                        {getDataSourceTypeIcon(dataSource.type)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <h4 className="font-medium text-gray-900 text-sm">
                          {getDataSourceTypeName(dataSource.type)}
                        </h4>
                        <p className="text-xs text-gray-600 truncate">
                          Product: {getProductName(dataSource.product_id)}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          Created {new Date(dataSource.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className="w-2 h-2 bg-green-400 rounded-full mr-1"></div>
                        <span className="text-xs text-green-600">Active</span>
                      </div>
                      <Link href={`/app/products/${dataSource.product_id}`}>
                        <Button variant="outline" size="sm">
                          View Product
                        </Button>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}