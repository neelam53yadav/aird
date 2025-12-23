'use client'

import { useState, useEffect } from 'react'
import { Loader2, BookOpen, AlertCircle } from 'lucide-react'
import { Label } from './ui/label'
import { apiClient, PlaybookInfo } from '@/lib/api-client'
import { useToast } from './ui/toast'

interface PlaybookSelectorProps {
  value?: string
  onChange: (playbookId: string | undefined) => void
  disabled?: boolean
  showDescription?: boolean
}

export function PlaybookSelector({
  value,
  onChange,
  disabled = false,
  showDescription = true,
}: PlaybookSelectorProps) {
  const [playbooks, setPlaybooks] = useState<PlaybookInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { addToast } = useToast()

  useEffect(() => {
    loadPlaybooks()
  }, [])

  const loadPlaybooks = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.listPlaybooks()
      if (response.error) {
        setError(response.error)
        addToast({
          type: 'error',
          message: `Failed to load playbooks: ${response.error}`,
        })
      } else if (response.data) {
        setPlaybooks(response.data)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load playbooks'
      setError(errorMessage)
      addToast({
        type: 'error',
        message: errorMessage,
      })
    } finally {
      setLoading(false)
    }
  }

  const selectedPlaybook = playbooks.find((pb) => pb.id === value)

  if (loading) {
    return (
      <div className="space-y-2">
        <Label>Preprocessing Playbook (Optional)</Label>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading playbooks...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-2">
        <Label>Preprocessing Playbook (Optional)</Label>
        <div className="flex items-center gap-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <Label htmlFor="playbook-select">
        Preprocessing Playbook <span className="text-gray-500 font-normal">(Optional)</span>
      </Label>
      <select
        id="playbook-select"
        value={value || ''}
        onChange={(e) => onChange(e.target.value || undefined)}
        disabled={disabled}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
      >
        <option value="">None (Auto-detect)</option>
        {playbooks.map((playbook) => (
          <option key={playbook.id} value={playbook.id}>
            {playbook.id}
          </option>
        ))}
      </select>
      {showDescription && selectedPlaybook && (
        <p className="text-sm text-gray-600 mt-1 flex items-start gap-2">
          <BookOpen className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <span>{selectedPlaybook.description}</span>
        </p>
      )}
      {showDescription && !value && (
        <p className="text-sm text-gray-500 mt-1">
          If no playbook is selected, the system will automatically detect the best playbook based on your content.
        </p>
      )}
    </div>
  )
}



