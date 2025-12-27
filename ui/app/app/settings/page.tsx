'use client'

import { useState, useEffect } from 'react'
import { Settings, User, Bell, Shield, Database, Key, Save, Eye, EyeOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import AppLayout from '@/components/layout/AppLayout'
import { useSession } from 'next-auth/react'
import { apiClient } from '@/lib/api-client'

export default function SettingsPage() {
  const { data: session } = useSession()
  const [activeTab, setActiveTab] = useState('profile')
  const [showApiKey, setShowApiKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saveMessage, setSaveMessage] = useState<{type: 'success' | 'error', text: string} | null>(null)
  const [settings, setSettings] = useState({
    // Profile settings
    firstName: '',
    lastName: '',
    email: session?.user?.email || '',
    timezone: 'UTC',
    
    // Notification settings
    emailNotifications: true,
    pipelineNotifications: true,
    billingNotifications: true,
    
    // Security settings
    twoFactorEnabled: false,
    sessionTimeout: '24',
    
    // API settings
    apiKey: 'pk_live_1234567890abcdef',
    openaiApiKey: '',
    openaiApiKeyConfigured: false,
    webhookUrl: '',
    workspaceId: '',
    
    // Workspace settings
    workspaceName: 'My Workspace',
    defaultLanguage: 'en',
    dateFormat: 'MM/DD/YYYY'
  })

  // Fetch workspace settings and user profile data on component mount
  useEffect(() => {
    const loadWorkspaceSettings = async () => {
      try {
        // First get workspaces to get the workspace ID
        const workspacesResponse = await apiClient.getWorkspaces()
        if (workspacesResponse.data && workspacesResponse.data.length > 0) {
          const workspaceId = workspacesResponse.data[0].id // Use first workspace
          setSettings(prev => ({ ...prev, workspaceId, workspaceName: workspacesResponse.data[0].name }))
          
          // Load workspace settings
          const settingsResponse = await apiClient.getWorkspaceSettings(workspaceId)
          if (settingsResponse.data) {
            setSettings(prev => ({
              ...prev,
              openaiApiKeyConfigured: settingsResponse.data.openai_api_key_configured || false,
              // Load the masked key to display in the input field
              openaiApiKey: settingsResponse.data.openai_api_key || '',
            }))
          }
        }
      } catch (error) {
        console.error('Failed to load workspace settings:', error)
      }
    }

    const fetchUserProfile = async () => {
      try {
        setLoading(true)
        const response = await apiClient.get('/api/v1/users/me')
        const userData = response.data
        
        if (userData) {
          // Use the full name from session if available, otherwise use the database fields
          const fullName = session?.user?.name || userData.name || ''
          const nameParts = fullName.split(' ')
          const firstName = nameParts[0] || userData.first_name || ''
          const lastName = nameParts.slice(1).join(' ') || userData.last_name || ''
          
          setSettings(prev => ({
            ...prev,
            firstName: firstName,
            lastName: lastName,
            email: session?.user?.email || userData.email || '',
            timezone: userData.timezone || 'UTC'
          }))
        }
      } catch (error) {
        console.error('Failed to fetch user profile:', error)
        // Fallback to session data if API fails
        if (session?.user?.name) {
          const nameParts = session.user.name.split(' ')
          setSettings(prev => ({
            ...prev,
            firstName: nameParts[0] || '',
            lastName: nameParts.slice(1).join(' ') || '',
            email: session.user.email || '',
          }))
        }
      } finally {
        setLoading(false)
      }
    }

    if (session) {
      // Load both workspace settings and user profile
      Promise.all([loadWorkspaceSettings(), fetchUserProfile()])
    } else {
      setLoading(false)
    }
  }, [session])

  const handleSave = async (section: string) => {
    try {
      setSaving(true)
      setSaveMessage(null)
      
      if (section === 'profile') {
        // Save profile changes to database
        const response = await apiClient.put('/api/v1/user/profile', {
          first_name: settings.firstName,
          last_name: settings.lastName,
          timezone: settings.timezone
        })
        
        // If we get here, the API call was successful
        setSaveMessage({type: 'success', text: 'Profile updated successfully!'})
        // Clear message after 3 seconds
        setTimeout(() => setSaveMessage(null), 3000)
      } else if (section === 'api' && settings.workspaceId) {
        // Save API settings (OpenAI key) to workspace settings
        // Only send the key if it's been changed (not the masked value)
        const apiKeyToSave = settings.openaiApiKey?.trim() || ''
        const isMaskedKey = apiKeyToSave.startsWith('sk-...') || apiKeyToSave.startsWith('sk-****')
        
        // Build request body
        // If the key is a masked placeholder or empty, don't send it to preserve the existing key
        // Only send if it's a new/updated key (starts with sk- but not sk-...)
        let requestBody: { openai_api_key?: string } = {}
        if (apiKeyToSave && !isMaskedKey) {
          // New or updated key - send it
          requestBody.openai_api_key = apiKeyToSave
        }
        // Otherwise, don't include openai_api_key in request (preserves existing key)
        // This prevents accidentally clearing the key when the input shows the masked value
        
        const response = await apiClient.updateWorkspaceSettings(settings.workspaceId, requestBody)
        
        if (response.error) {
          setSaveMessage({type: 'error', text: response.error || 'Failed to save API settings'})
        } else {
          setSaveMessage({type: 'success', text: 'API settings saved successfully!'})
          // Update configured status and masked key
          setSettings(prev => ({ 
            ...prev, 
            openaiApiKeyConfigured: response.data?.openai_api_key_configured || false,
            // Reload the masked key after saving
            openaiApiKey: response.data?.openai_api_key || ''
          }))
        }
        setTimeout(() => setSaveMessage(null), 3000)
      } else {
        // For other sections, use existing mock behavior
        console.log(`Saving ${section} settings:`, settings)
        setSaveMessage({type: 'success', text: `${section} settings saved!`})
        setTimeout(() => setSaveMessage(null), 3000)
      }
    } catch (error) {
      console.error(`Failed to save ${section} settings:`, error)
      setSaveMessage({type: 'error', text: 'An error occurred while saving. Please try again.'})
      setTimeout(() => setSaveMessage(null), 5000)
    } finally {
      setSaving(false)
    }
  }

  const tabs = [
    { id: 'profile', name: 'Profile', icon: User },
    { id: 'notifications', name: 'Notifications', icon: Bell },
    { id: 'security', name: 'Security', icon: Shield },
    { id: 'api', name: 'API & Integrations', icon: Key },
    { id: 'workspace', name: 'Workspace', icon: Database }
  ]

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
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-600 mt-2">Configure your account and system preferences</p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar Navigation */}
          <div className="lg:w-64">
            <nav className="space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                      activeTab === tab.id
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="h-4 w-4 mr-3" />
                    {tab.name}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Main Content */}
          <div className="flex-1">
            {/* Profile Settings */}
            {activeTab === 'profile' && (
              <div className="bg-white shadow rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Profile Information</h3>
                  <p className="text-sm text-gray-600">Update your personal information</p>
                </div>
                <div className="p-6 space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                      <input
                        type="text"
                        value={settings.firstName}
                        onChange={(e) => setSettings({...settings, firstName: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                      <input
                        type="text"
                        value={settings.lastName}
                        onChange={(e) => setSettings({...settings, lastName: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                    <input
                      type="email"
                      value={settings.email}
                      disabled
                      className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500 cursor-not-allowed"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Email address is tied to your login account and cannot be changed here. 
                      To change your email, please contact your administrator or update it in your authentication provider.
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
                    <select
                      value={settings.timezone}
                      onChange={(e) => setSettings({...settings, timezone: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="UTC">UTC</option>
                      <option value="America/New_York">Eastern Time</option>
                      <option value="America/Chicago">Central Time</option>
                      <option value="America/Denver">Mountain Time</option>
                      <option value="America/Los_Angeles">Pacific Time</option>
                    </select>
                  </div>
                  {/* Save Message */}
                  {saveMessage && (
                    <div className={`p-3 rounded-md ${
                      saveMessage.type === 'success' 
                        ? 'bg-green-50 text-green-800 border border-green-200' 
                        : 'bg-red-50 text-red-800 border border-red-200'
                    }`}>
                      {saveMessage.text}
                    </div>
                  )}
                  
                  <div className="flex justify-end">
                    <Button 
                      onClick={() => handleSave('profile')}
                      disabled={saving}
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Notification Settings */}
            {activeTab === 'notifications' && (
              <div className="bg-white shadow rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Notification Preferences</h3>
                  <p className="text-sm text-gray-600">Choose how you want to be notified</p>
                </div>
                <div className="p-6 space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">Email Notifications</h4>
                        <p className="text-sm text-gray-600">Receive notifications via email</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.emailNotifications}
                          onChange={(e) => setSettings({...settings, emailNotifications: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">Pipeline Notifications</h4>
                        <p className="text-sm text-gray-600">Get notified when pipelines complete or fail</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.pipelineNotifications}
                          onChange={(e) => setSettings({...settings, pipelineNotifications: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">Billing Notifications</h4>
                        <p className="text-sm text-gray-600">Receive billing and subscription updates</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.billingNotifications}
                          onChange={(e) => setSettings({...settings, billingNotifications: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <Button 
                      onClick={() => handleSave('notifications')}
                      disabled={saving}
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Security Settings */}
            {activeTab === 'security' && (
              <div className="bg-white shadow rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Security Settings</h3>
                  <p className="text-sm text-gray-600">Manage your account security</p>
                </div>
                <div className="p-6 space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">Two-Factor Authentication</h4>
                        <p className="text-sm text-gray-600">Add an extra layer of security to your account</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.twoFactorEnabled}
                          onChange={(e) => setSettings({...settings, twoFactorEnabled: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Session Timeout</label>
                      <select
                        value={settings.sessionTimeout}
                        onChange={(e) => setSettings({...settings, sessionTimeout: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="1">1 hour</option>
                        <option value="8">8 hours</option>
                        <option value="24">24 hours</option>
                        <option value="168">7 days</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <Button 
                      onClick={() => handleSave('security')}
                      disabled={saving}
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* API Settings */}
            {activeTab === 'api' && (
              <div className="bg-white shadow rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">API & Integrations</h3>
                  <p className="text-sm text-gray-600">Manage your API keys and webhooks</p>
                </div>
                <div className="p-6 space-y-6">
                  {/* OpenAI API Key Section */}
                  <div className="border-b border-gray-200 pb-6">
                    <h4 className="text-md font-medium text-gray-900 mb-2">OpenAI API Key</h4>
                    <p className="text-sm text-gray-600 mb-4">
                      Configure your OpenAI API key to use OpenAI embedding models (text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large).
                      Get your API key from{' '}
                      <a 
                        href="https://platform.openai.com/api-keys" 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 underline"
                      >
                        OpenAI Platform
                      </a>
                    </p>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">OpenAI API Key</label>
                      <div className="flex items-center space-x-2">
                        <input
                          type={showApiKey ? "text" : "password"}
                          value={settings.openaiApiKey || ''}
                          onChange={(e) => setSettings({...settings, openaiApiKey: e.target.value})}
                          placeholder={settings.openaiApiKeyConfigured ? "sk-...****" : "sk-your-api-key-here"}
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowApiKey(!showApiKey)}
                        >
                          {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                      {settings.openaiApiKeyConfigured && !showApiKey && (
                        <p className="text-xs text-green-600 mt-1">✓ OpenAI API key is configured</p>
                      )}
                      <p className="text-xs text-gray-500 mt-1">Keep your API key secure and never share it publicly</p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
                    <input
                      type="url"
                      value={settings.webhookUrl}
                      onChange={(e) => setSettings({...settings, webhookUrl: e.target.value})}
                      placeholder="https://your-domain.com/webhook"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Receive real-time notifications about your data pipelines</p>
                  </div>
                  
                  <div className="flex justify-end">
                    <Button 
                      onClick={() => handleSave('api')}
                      disabled={saving}
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Workspace Settings */}
            {activeTab === 'workspace' && (
              <div className="bg-white shadow rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Workspace Settings</h3>
                  <p className="text-sm text-gray-600">Configure your workspace preferences</p>
                </div>
                <div className="p-6 space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Workspace Name</label>
                    <input
                      type="text"
                      value={settings.workspaceName}
                      onChange={(e) => setSettings({...settings, workspaceName: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Default Language</label>
                      <select
                        value={settings.defaultLanguage}
                        onChange={(e) => setSettings({...settings, defaultLanguage: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="en">English</option>
                        <option value="es">Spanish</option>
                        <option value="fr">French</option>
                        <option value="de">German</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Date Format</label>
                      <select
                        value={settings.dateFormat}
                        onChange={(e) => setSettings({...settings, dateFormat: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                        <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                        <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                      </select>
                    </div>
                  </div>
                  
                  <div className="flex justify-end">
                    <Button 
                      onClick={() => handleSave('workspace')}
                      disabled={saving}
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
