'use client'

import { useState, useEffect } from 'react'
import { Users, UserPlus, Shield, Mail, MoreVertical, Trash2, Edit } from 'lucide-react'
import { Button } from '@/components/ui/button'
import AppLayout from '@/components/layout/AppLayout'
import { apiClient } from '@/lib/api-client'
import { useSession } from 'next-auth/react'

interface TeamMember {
  id: string
  user_id: string
  email: string
  name: string
  role: 'owner' | 'admin' | 'editor' | 'viewer'
  created_at: string
}

export default function TeamPage() {
  const { data: session } = useSession()
  const [members, setMembers] = useState<TeamMember[]>([])
  const [loading, setLoading] = useState(true)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<'admin' | 'editor' | 'viewer'>('viewer')
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [memberToDelete, setMemberToDelete] = useState<TeamMember | null>(null)

  // Get workspace ID from session or use default for testing
  const workspaceId = session?.user?.workspace_ids?.[0] || '550e8400-e29b-41d4-a716-446655440001'

  useEffect(() => {
    loadTeamMembers()
  }, [])

  const loadTeamMembers = async () => {
    try {
      setLoading(true)
      // For now, we'll use mock data since the API endpoint doesn't exist yet
      // In a real implementation, this would be: await apiClient.get(`/api/v1/workspaces/${workspaceId}/members`)
      const mockMembers: TeamMember[] = [
        {
          id: '1',
          user_id: 'user-1',
          email: 'john.doe@company.com',
          name: 'John Doe',
          role: 'owner',
          created_at: '2024-01-15T10:00:00Z'
        },
        {
          id: '2',
          user_id: 'user-2',
          email: 'jane.smith@company.com',
          name: 'Jane Smith',
          role: 'admin',
          created_at: '2024-01-20T14:30:00Z'
        },
        {
          id: '3',
          user_id: 'user-3',
          email: 'bob.wilson@company.com',
          name: 'Bob Wilson',
          role: 'editor',
          created_at: '2024-02-01T09:15:00Z'
        }
      ]
      setMembers(mockMembers)
    } catch (err) {
      console.error('Failed to load team members:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleInviteMember = async () => {
    if (!inviteEmail || !inviteRole) return
    
    try {
      // In a real implementation, this would be:
      // await apiClient.post(`/api/v1/workspaces/${workspaceId}/members`, {
      //   email: inviteEmail,
      //   role: inviteRole
      // })
      
      console.log('Inviting member:', { email: inviteEmail, role: inviteRole })
      setShowInviteModal(false)
      setInviteEmail('')
      setInviteRole('viewer')
      // Reload members after successful invite
      loadTeamMembers()
    } catch (err) {
      console.error('Failed to invite member:', err)
    }
  }

  const handleRemoveMember = (member: TeamMember) => {
    setMemberToDelete(member)
    setShowDeleteModal(true)
  }

  const confirmRemoveMember = async () => {
    if (!memberToDelete) return
    
    try {
      // In a real implementation, this would be:
      // await apiClient.delete(`/api/v1/workspaces/${workspaceId}/members/${memberToDelete.id}`)
      
      console.log('Removing member:', memberToDelete.id)
      setMembers(members.filter(m => m.id !== memberToDelete.id))
      setShowDeleteModal(false)
      setMemberToDelete(null)
    } catch (err) {
      console.error('Failed to remove member:', err)
    }
  }

  const cancelRemoveMember = () => {
    setShowDeleteModal(false)
    setMemberToDelete(null)
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'owner': return 'bg-purple-100 text-purple-800'
      case 'admin': return 'bg-red-100 text-red-800'
      case 'editor': return 'bg-blue-100 text-blue-800'
      case 'viewer': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'owner': return <Shield className="h-4 w-4" />
      case 'admin': return <Shield className="h-4 w-4" />
      case 'editor': return <Edit className="h-4 w-4" />
      case 'viewer': return <Users className="h-4 w-4" />
      default: return <Users className="h-4 w-4" />
    }
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
          <h1 className="text-3xl font-bold text-gray-900">Team Management</h1>
          <p className="text-gray-600 mt-2">Manage team members and their access to workspaces</p>
        </div>

        {/* Header with Invite Button */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Team Members</h2>
            <p className="text-sm text-gray-600">{members.length} member{members.length !== 1 ? 's' : ''}</p>
          </div>
          <Button onClick={() => setShowInviteModal(true)}>
            <UserPlus className="h-4 w-4 mr-2" />
            Invite Member
          </Button>
        </div>

        {/* Team Members List */}
        <div className="bg-white shadow rounded-lg">
          <div className="divide-y divide-gray-200">
            {members.map((member) => (
              <div key={member.id} className="px-6 py-4 flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="flex-shrink-0">
                    <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                      <Users className="h-5 w-5 text-gray-500" />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <h3 className="text-sm font-medium text-gray-900">{member.name}</h3>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRoleBadgeColor(member.role)}`}>
                        {getRoleIcon(member.role)}
                        <span className="ml-1 capitalize">{member.role}</span>
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">{member.email}</p>
                    <p className="text-xs text-gray-400">
                      Joined {new Date(member.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {member.role !== 'owner' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRemoveMember(member)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Role Permissions Info */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-4">Role Permissions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Shield className="h-5 w-5 text-purple-600" />
                <span className="font-medium text-gray-900">Owner</span>
              </div>
              <p className="text-sm text-gray-600">Full access to all features, billing, and team management</p>
            </div>
            <div className="bg-white rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Shield className="h-5 w-5 text-red-600" />
                <span className="font-medium text-gray-900">Admin</span>
              </div>
              <p className="text-sm text-gray-600">Manage products, data sources, and team members</p>
            </div>
            <div className="bg-white rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Edit className="h-5 w-5 text-blue-600" />
                <span className="font-medium text-gray-900">Editor</span>
              </div>
              <p className="text-sm text-gray-600">Create and edit products and data sources</p>
            </div>
            <div className="bg-white rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Users className="h-5 w-5 text-gray-600" />
                <span className="font-medium text-gray-900">Viewer</span>
              </div>
              <p className="text-sm text-gray-600">View products, data sources, and analytics</p>
            </div>
          </div>
        </div>

        {/* Invite Modal */}
        {showInviteModal && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Invite Team Member</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="colleague@company.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as 'admin' | 'editor' | 'viewer')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end space-x-3 mt-6">
                <Button variant="outline" onClick={() => setShowInviteModal(false)}>
                  Cancel
                </Button>
                <Button onClick={handleInviteMember}>
                  Send Invite
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteModal && memberToDelete && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              <div className="flex items-center space-x-3 mb-4">
                <div className="flex-shrink-0">
                  <div className="h-10 w-10 rounded-full bg-red-100 flex items-center justify-center">
                    <Trash2 className="h-5 w-5 text-red-600" />
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Remove Team Member</h3>
                  <p className="text-sm text-gray-600">This action cannot be undone</p>
                </div>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <div className="flex items-center space-x-3">
                  <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center">
                    <Users className="h-4 w-4 text-gray-500" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{memberToDelete.name}</p>
                    <p className="text-xs text-gray-500">{memberToDelete.email}</p>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getRoleBadgeColor(memberToDelete.role)}`}>
                      {getRoleIcon(memberToDelete.role)}
                      <span className="ml-1 capitalize">{memberToDelete.role}</span>
                    </span>
                  </div>
                </div>
              </div>

              <p className="text-sm text-gray-600 mb-6">
                Are you sure you want to remove <strong>{memberToDelete.name}</strong> from the team? 
                They will lose access to this workspace and all its data.
              </p>

              <div className="flex justify-end space-x-3">
                <Button variant="outline" onClick={cancelRemoveMember}>
                  Cancel
                </Button>
                <Button 
                  onClick={confirmRemoveMember}
                  className="bg-red-600 hover:bg-red-700 text-white"
                >
                  Remove Member
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
