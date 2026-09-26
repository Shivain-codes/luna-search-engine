import { Typography } from './Typography'
import { Badge } from './Badge'
import { Skeleton } from './Skeleton'
import type { KnowledgeContext } from '@/types/search'
import { VisualService } from '@/services/visuals'

interface KnowledgePanelProps {
  data: KnowledgeContext | null
  isLoading?: boolean
}

export const KnowledgePanel = ({ data, isLoading }: KnowledgePanelProps) => {
  if (isLoading) {
    return (
      <div className="glass p-6 rounded-3xl space-y-4 w-full max-w-sm">
        <Skeleton className="h-48 w-full rounded-2xl" />
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <div className="space-y-2 pt-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
        </div>
      </div>
    )
  }

  if (!data) return null

  // Resolve a high-quality image if the backend didn't provide one
  const entityImage = data.image || VisualService.getEntityImage(data.name, data.category)

  return (
    <div className="glass p-6 rounded-3xl space-y-6 w-full max-w-sm sticky top-32 shadow-sm border-slate-200 dark:border-slate-800">
      <div className="space-y-4">
        <div className="aspect-square w-full bg-slate-100 dark:bg-slate-800 rounded-2xl overflow-hidden relative group">
          <img
            src={entityImage}
            alt={data.name}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            onError={(e) => {
              (e.target as HTMLImageElement).src = 'https://via.placeholder.com/400x400?text=No+Image'
            }}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <Typography variant="h3" weight="bold" className="truncate">
              {data.name}
            </Typography>
            <Badge variant="default" className="shrink-0">{data.category || 'Entity'}</Badge>
          </div>
        </div>

        <Typography variant="p" className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          {data.description || 'No description available for this entity.'}
        </Typography>
      </div>

      <div className="space-y-3 pt-4 border-t border-slate-200 dark:border-slate-800">
        <Typography variant="small" weight="semibold" className="uppercase tracking-wider text-slate-500">
          Quick Facts
        </Typography>
        <div className="grid grid-cols-1 gap-2">
          {data.facts && Object.entries(data.facts).map(([key, value]) => (
            <div key={key} className="flex justify-between text-sm p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors">
              <span className="text-slate-500">{key}:</span>
              <span className="font-medium text-slate-900 dark:text-slate-100">{String(value)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
