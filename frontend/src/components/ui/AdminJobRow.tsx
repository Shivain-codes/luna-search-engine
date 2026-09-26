import { Button } from './Button'
import { Badge } from './Badge'
import { Typography } from './Typography'
import type { CrawlJob, CrawlStatus } from '@/types/admin'

interface AdminJobRowProps {
  job: CrawlJob
  onAction: (id: string, action: string) => void
  onRun: (id: string) => void
  isRunning: boolean
}

const statusVariant: Record<CrawlStatus, 'default' | 'success' | 'error' | 'warning' | 'info'> = {
  pending: 'warning',
  running: 'info',
  paused: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'error',
}

export const AdminJobRow = ({ job, onAction, onRun }: AdminJobRowProps) => {
  const progress = job.total_pages ? (job.pages_crawled / job.total_pages) * 100 : 0

  return (
    <div className="flex items-center justify-between p-4 border border-slate-200 dark:border-slate-800 rounded-2xl hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-all duration-200 group">
      <div className="flex-1 min-w-0 mr-4">
        <div className="flex items-center gap-3 mb-2">
          <Typography variant="p" weight="semibold" className="truncate">
            {job.name}
          </Typography>
          <Badge variant={statusVariant[job.status]}>{job.status}</Badge>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex-1 max-w-xs">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-500">Progress</span>
              <span className="font-mono">{Math.round(progress)}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className="flex gap-3 text-xs font-mono">
            <span className="text-slate-500">Crawl: <span className="text-slate-900 dark:text-slate-100">{job.pages_crawled}</span></span>
            <span className="text-slate-500">Fail: <span className="text-red-500">{job.pages_failed}</span></span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        {job.status === 'running' && (
          <Button size="sm" variant="ghost" onClick={() => onAction(job.id, 'pause')}>
            Pause
          </Button>
        )}
        {job.status === 'paused' && (
          <Button size="sm" variant="ghost" onClick={() => onAction(job.id, 'resume')}>
            Resume
          </Button>
        )}
        {job.status !== 'running' && job.status !== 'paused' && (
          <Button size="sm" variant="primary" onClick={() => onRun(job.id)}>
            Run
          </Button>
        )}
      </div>
    </div>
  )
}
