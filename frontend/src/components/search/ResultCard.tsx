import React from 'react'
import { SearchResult } from '@/types/search'
import { Typography } from '@/components/ui/Typography'
import { VisualService } from '@/services/visuals'

interface Props {
  result: SearchResult
  position: number
  onSelect: (documentId: string, position: number) => void
}

function getBreadcrumbs(url: string) {
  try {
    const parsed = new URL(url)
    const pathSegments = parsed.pathname.split('/').filter(Boolean)
    return {
      host: parsed.hostname,
      segments: pathSegments,
    }
  } catch {
    return { host: url, segments: [] }
  }
}

export function ResultCard({ result, position, onSelect }: Props) {
  const { host, segments } = getBreadcrumbs(result.url)
  const logoUrl = VisualService.getLogo(host)

  return (
    <article
      className="group p-4 rounded-2xl transition-all duration-200 hover:bg-slate-100 dark:hover:bg-slate-900/50 flex gap-4"
      onClick={() => onSelect(result.id, position)}
    >
      <div className="flex-1">
        <a
          href={result.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block space-y-1"
        >
          {/* Breadcrumbs / URL */}
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <img
              src={logoUrl}
              alt=""
              className="w-4 h-4 rounded-sm"
              onError={(e) => {
                (e.target as HTMLImageElement).src = `https://www.google.com/s2/favicons?sz=64&domain=${host}`
              }}
            />
            <div className="flex items-center gap-1 truncate">
              <span className="font-medium text-slate-700 dark:text-slate-300">{host}</span>
              {segments.map((seg, i) => (
                <React.Fragment key={i}>
                  <span className="text-slate-400">›</span>
                  <span className="truncate">{seg}</span>
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Title */}
          <Typography
            variant="h4"
            weight="semibold"
            className="text-blue-600 dark:text-blue-400 group-hover:underline decoration-2 underline-offset-2"
          >
            {result.title || result.url}
          </Typography>

          {/* Snippet */}
          <Typography variant="p" className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed line-clamp-2">
            {result.snippet}
          </Typography>
        </a>
      </div>

      {/* Rich Result Thumbnail */}
      <div className="hidden sm:block w-24 h-16 shrink-0 rounded-lg overflow-hidden bg-slate-200 dark:bg-slate-800">
        <img
          src={result.images && result.images[0] ? result.images[0] : `https://source.unsplash.com/featured/?${encodeURIComponent(result.title || 'web')},technology`}
          alt=""
          className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
          onError={(e) => {
            (e.target as HTMLImageElement).src = `https://www.google.com/s2/favicons?sz=128&domain=${host}`
          }}
        />
      </div>
    </article>
  )
}
