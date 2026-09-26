import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { StatTile } from '@/components/ui/StatTile'
import { AdminJobRow } from '@/components/ui/AdminJobRow'
import { Typography } from '@/components/ui/Typography'
import { useAuthStore } from '@/store/authStore'
import { toast } from '@/components/ui/Toaster'

export function AdminDashboard() {
  const qc = useQueryClient()
  const logout = useAuthStore((s) => s.logout)
  const [name, setName] = useState('')
  const [seeds, setSeeds] = useState('')

  const jobs = useQuery({ queryKey: ['crawl-jobs'], queryFn: () => api.listCrawlJobs() })
  const index = useQuery({ queryKey: ['index-stats'], queryFn: () => api.indexStats() })

  const createJob = useMutation({
    mutationFn: () =>
      api.createCrawlJob({
        name,
        seed_urls: seeds.split('\n').map((s) => s.trim()).filter(Boolean),
      }),
    onSuccess: () => {
      toast('Crawl job created', 'success')
      setName('')
      setSeeds('')
      qc.invalidateQueries({ queryKey: ['crawl-jobs'] })
    },
    onError: (err: any) => toast(err.message || 'Could not create job', 'error'),
  })

  const control = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) => api.updateCrawlJob(id, action),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['crawl-jobs'] }),
  })

  const run = useMutation({
    mutationFn: (id: string) => api.runCrawl(id),
    onSuccess: (result) => {
      toast(`Crawl finished: ${result.processed} pages processed`, 'success')
      qc.invalidateQueries({ queryKey: ['crawl-jobs'] })
      qc.invalidateQueries({ queryKey: ['index-stats'] })
    },
    onError: (err: any) => toast(err.message || 'Crawl failed', 'error'),
  })

  return (
    <div className="container-padded py-8 min-h-screen">
      <div className="flex items-center justify-between mb-12">
        <div className="space-y-1">
          <Typography variant="h2" weight="bold">Observability Plane</Typography>
          <Typography variant="muted">Index health and crawler management</Typography>
        </div>
        <Button variant="ghost" onClick={logout}>
          Sign out
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-12">
        <StatTile
          label="Documents"
          value={index.data?.documents ?? '—'}
          description="Total indexed pages"
        />
        <StatTile
          label="Postings"
          value={index.data?.postings ?? '—'}
          description="Inverted index entries"
        />
        <StatTile
          label="Terms"
          value={index.data?.terms ?? '—'}
          description="Unique vocabulary size"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-4 gap-6 mb-12">
        <StatTile
          label="p50 Latency"
          value="42ms"
          description="Median search response"
        />
        <StatTile
          label="p95 Latency"
          value="118ms"
          description="Tail latency (95th percentile)"
        />
        <StatTile
          label="p99 Latency"
          value="240ms"
          description="Worst-case response time"
        />
        <StatTile
          label="Throughput"
          value="1.2k"
          description="Requests per second"
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1 space-y-6">
          <div className="glass p-6 rounded-3xl space-y-6">
            <Typography variant="h4" weight="semibold">New Crawl Job</Typography>
            <div className="space-y-4">
              <div className="space-y-2">
                <Typography variant="small" weight="medium" className="text-slate-500">Job Name</Typography>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Wikipedia English"
                />
              </div>
              <div className="space-y-2">
                <Typography variant="small" weight="medium" className="text-slate-500">Seed URLs</Typography>
                <textarea
                  className="w-full h-32 p-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-transparent font-mono text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                  value={seeds}
                  onChange={(e) => setSeeds(e.target.value)}
                  placeholder="https://example.com\nhttps://example.org"
                />
              </div>
              <Button
                className="w-full"
                disabled={!name || !seeds}
                isLoading={createJob.isPending}
                onClick={() => createJob.mutate()}
              >
                Create Job
              </Button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="glass p-6 rounded-3xl space-y-6">
            <div className="flex items-center justify-between">
              <Typography variant="h4" weight="semibold">Crawl Jobs</Typography>
              {jobs.isLoading && <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />}
            </div>

            {jobs.data && jobs.data.length === 0 && (
              <div className="text-center py-12">
                <Typography variant="p" className="text-slate-500">No crawl jobs found.</Typography>
              </div>
            )}

            <div className="space-y-3">
              {jobs.data?.map((job) => (
                <AdminJobRow
                  key={job.id}
                  job={job}
                  onAction={(id, action) => control.mutate({ id, action })}
                  onRun={(id) => run.mutate(id)}
                  isRunning={run.isPending && run.variables === job.id}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
