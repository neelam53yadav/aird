'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Plus, Package, MoreVertical, Trash2, Edit } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ConfirmModal, ResultModal } from '@/components/ui/modal'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient } from '@/lib/api-client'

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

export default function ProductsPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteProductId, setDeleteProductId] = useState<string | null>(null)
  const [showResultModal, setShowResultModal] = useState(false)
  const [resultModalData, setResultModalData] = useState<{
    type: 'success' | 'error' | 'warning' | 'info'
    title: string
    message: string
  } | null>(null)
  const [openDropdown, setOpenDropdown] = useState<string | null>(null)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/')
      return
    }

    if (status === 'authenticated') {
      loadProducts()
    }
  }, [status, router])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      setOpenDropdown(null)
    }

    if (openDropdown) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [openDropdown])

  const loadProducts = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getProducts()
      
      if (response.error) {
        setError(response.error)
      } else {
        setProducts((response.data as Product[]) || [])
      }
    } catch (err) {
      setError('Failed to load products')
    } finally {
      setLoading(false)
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

  const handleDeleteProduct = (productId: string) => {
    setDeleteProductId(productId)
    setShowDeleteModal(true)
    setOpenDropdown(null)
  }

  const confirmDeleteProduct = async () => {
    if (!deleteProductId) return

    try {
      const response = await apiClient.deleteProduct(deleteProductId)
      
      if (response.error) {
        setResultModalData({
          type: 'error',
          title: 'Delete Failed',
          message: response.error
        })
      } else {
        // Remove the product from the list
        setProducts(products.filter(p => p.id !== deleteProductId))
        setResultModalData({
          type: 'success',
          title: 'Product Deleted',
          message: 'Product has been successfully deleted'
        })
      }
      setShowResultModal(true)
    } catch (err) {
      setResultModalData({
        type: 'error',
        title: 'Delete Failed',
        message: 'Failed to delete product'
      })
      setShowResultModal(true)
    } finally {
      setShowDeleteModal(false)
      setDeleteProductId(null)
    }
  }

  const getStatusDescription = (status: string) => {
    switch (status) {
      case 'draft': return 'Product is being configured and not yet running'
      case 'running': return 'Product is actively processing data'
      case 'ready': return 'Product is ready for use'
      case 'failed': return 'Product encountered an error and needs attention'
      default: return 'Unknown status'
    }
  }

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading products...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Error: {error}</p>
          <Button onClick={loadProducts}>Try Again</Button>
        </div>
      </div>
    )
  }

  return (
    <AppLayout>
      <div className="p-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Products</h1>
              <p className="text-gray-600">Manage your data products and pipelines</p>
            </div>
            <Link href="/app/products/new">
              <Button className="flex items-center">
                <Plus className="h-4 w-4 mr-2" />
                New Product
              </Button>
            </Link>
          </div>
        </div>

        {/* Content */}
        <div>
        {products.length === 0 ? (
          <div className="text-center py-12">
            <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No products yet</h3>
            <p className="text-gray-600 mb-6">Get started by creating your first data product.</p>
            <Link href="/app/products/new">
              <Button className="flex items-center mx-auto">
                <Plus className="h-4 w-4 mr-2" />
                Create Product
              </Button>
            </Link>
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {products.map((product) => (
              <div key={product.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      <Link 
                        href={`/app/products/${product.id}`}
                        className="hover:text-blue-600 transition-colors"
                      >
                        {product.name}
                      </Link>
                    </h3>
                    <div className="flex items-center mb-3">
                      <span 
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(product.status)}`}
                        title={getStatusDescription(product.status)}
                      >
                        {product.status}
                      </span>
                      <span className="ml-2 text-sm text-gray-500">v{product.current_version}</span>
                    </div>
                    <p className="text-sm text-gray-600">
                      Created {new Date(product.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="relative">
                    <button 
                      className="text-gray-400 hover:text-gray-600"
                      onClick={() => setOpenDropdown(openDropdown === product.id ? null : product.id)}
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>
                    {openDropdown === product.id && (
                      <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border border-gray-200 z-10">
                        <div className="py-1">
                          <button
                            className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                            onClick={() => {
                              setOpenDropdown(null)
                              router.push(`/app/products/${product.id}/edit`)
                            }}
                          >
                            <Edit className="h-4 w-4 mr-2" />
                            Edit Product
                          </button>
                          <button
                            className="flex items-center w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                            onClick={() => handleDeleteProduct(product.id)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete Product
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                <div className="mt-4 flex space-x-2">
                  <Link href={`/app/products/${product.id}`} className="flex-1">
                    <Button variant="outline" size="sm" className="w-full">
                      View Details
                    </Button>
                  </Link>
                  <Link href={`/app/products/${product.id}/datasources/new`}>
                    <Button size="sm" className="flex-1">
                      Add Data Source
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
        </div>

        {/* Modals */}
        <ConfirmModal
          isOpen={showDeleteModal}
          onClose={() => {
            setShowDeleteModal(false)
            setDeleteProductId(null)
          }}
          onConfirm={confirmDeleteProduct}
          title="Delete Product"
          message="Are you sure you want to delete this product? This action cannot be undone and will also delete all associated data sources."
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
      </div>
    </AppLayout>
  )
}
