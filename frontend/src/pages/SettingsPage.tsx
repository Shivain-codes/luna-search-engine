import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '@/services/api'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Spinner } from '@/components/ui/Spinner'
import { toast } from '@/components/ui/Toaster'

export function SettingsPage() {
  const qc = useQueryClient()
  const settings = useQuery({ queryKey: ['settings'], queryFn: () => api.listSettings() })
  const keys = useQuery({ queryKey: ['api-keys'], queryFn: () => api.listApiKeys() })
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState<string | null>(null)

  const createKey = useMutation({
    mutationFn: () => api.createApiKey(newKeyName),
    onSuccess: (data) => {
      setCreatedKey(data.key)
      setNewKeyName('')
      qc.invalidateQueries({ queryKey: ['api-keys'] })
    },
    onError: () => toast('Could not create key', 'error'),
  })

  const revoke = useMutation({
    mutationFn: (id: string) => api.revokeApiKey(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys'] }),
  })

  return (
    <div className="container-padded py-6 space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <Card>
        <h2 className="font-medium mb-3">Configuration</h2>
        {settings.isLoading && <Spinner />}
        {settings.data && settings.data.length === 0 && (
          <p className="text-slate-500 text-sm">No custom settings configured.</p>
        )}
        <ul className="divide-y divide-slate-200 dark:divide-slate-700">
          {settings.data?.map((s) => (
            <li key={s.key} className="flex justify-between py-2 text-sm">
              <span className="font-mono">{s.key}</span>
              <span className="text-slate-500">{s.value}</span>
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <h2 className="font-medium mb-3">API keys</h2>
        <div className="flex gap-2 mb-4">
          <Input
            placeholder="Key name"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
          />
          <Button disabled={!newKeyName} isLoading={createKey.isPending} onClick={() => createKey.mutate()}>
            Create
          </Button>
        </div>
        {createdKey && (
          <div className="mb-4 p-3 rounded-lg bg-accent-50 dark:bg-accent-900/30 text-sm">
            <p className="font-medium mb-1">Copy this key now — it is shown only once:</p>
            <code className="break-all font-mono">{createdKey}</code>
          </div>
        )}
        <ul className="divide-y divide-slate-200 dark:divide-slate-700">
          {keys.data?.map((k) => (
            <li key={k.id} className="flex items-center justify-between py-2 text-sm">
              <div>
                <span className="font-mono">{k.key_prefix}…</span>
                <span className="ml-2 text-slate-500">{k.name}</span>
                {!k.is_active && <span className="ml-2 badge-danger">revoked</span>}
              </div>
              {k.is_active && (
                <Button size="sm" variant="danger" onClick={() => revoke.mutate(k.id)}>
                  Revoke
                </Button>
              )}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
