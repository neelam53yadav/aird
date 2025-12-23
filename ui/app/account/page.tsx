"use client"

import { useSession } from "next-auth/react"
import { useEffect, useState } from "react"
import { exchangeToken } from "@/lib/auth-utils"

interface User {
  id: string
  email: string
  name: string
  roles: string[]
  picture_url?: string
}

interface Workspace {
  id: string
  name: string
  role: string
  created_at: string
}

export default function AccountPage() {
  const { data: session, status } = useSession()
  const [user, setUser] = useState<User | null>(null)
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (status === "authenticated") {
      // Exchange NextAuth token for backend token
      exchangeToken()
        .then(() => {
          // Fetch user profile
          return fetch("/api/v1/users/me", {
            headers: {
              "Authorization": `Bearer ${document.cookie
                .split("; ")
                .find(row => row.startsWith("primedata_api_token="))
                ?.split("=")[1] || ""}`,
            },
          })
        })
        .then(res => res.json())
        .then(data => {
          setUser(data)
          // Fetch workspaces
          return fetch("/api/v1/workspaces", {
            headers: {
              "Authorization": `Bearer ${document.cookie
                .split("; ")
                .find(row => row.startsWith("primedata_api_token="))
                ?.split("=")[1] || ""}`,
            },
          })
        })
        .then(res => res.json())
        .then(data => {
          setWorkspaces(data)
          setLoading(false)
        })
        .catch(error => {
          console.error("Error fetching user data:", error)
          setLoading(false)
        })
    }
  }, [status])

  if (status === "loading" || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (status === "unauthenticated") {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Access Denied</h1>
          <p className="text-gray-600">Please sign in to access this page.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Account</h1>
          
          {/* User Profile */}
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Profile</h2>
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <p className="text-gray-900">{user?.name || session?.user?.name}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <p className="text-gray-900">{user?.email || session?.user?.email}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Roles
                </label>
                <div className="flex flex-wrap gap-2">
                  {(user?.roles || ["viewer"]).map((role) => (
                    <span
                      key={role}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                    >
                      {role}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Profile Picture
                </label>
                {user?.picture_url || session?.user?.image ? (
                  <img
                    src={user?.picture_url || session?.user?.image || undefined}
                    alt="Profile"
                    className="w-16 h-16 rounded-full"
                  />
                ) : (
                  <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-gray-500 text-lg">
                      {(user?.name || session?.user?.name || "U")[0].toUpperCase()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Workspaces */}
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Workspaces</h2>
            {workspaces.length > 0 ? (
              <div className="space-y-4">
                {workspaces.map((workspace) => (
                  <div
                    key={workspace.id}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-gray-900">
                          {workspace.name}
                        </h3>
                        <p className="text-sm text-gray-500">
                          Created {new Date(workspace.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        {workspace.role}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No workspaces found.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
