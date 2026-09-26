import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { SearchInput } from '@/components/ui/SearchInput'
import { ResultCard } from '@/components/search/ResultCard'
import { Pagination } from '@/components/search/Pagination'
import { Skeleton } from '@/components/ui/Skeleton'
import { FilterBar } from '@/components/ui/FilterBar'
import { AnswerBox } from '@/components/ui/AnswerBox'
import { KnowledgePanel } from '@/components/ui/KnowledgePanel'
import { Typography } from '@/components/ui/Typography'
import { Button } from '@/components/ui/Button'
import { useSearch } from '@/hooks/useSearch'
import { useClickTracking } from '@/hooks/useClickTracking'
import { useSearchStore } from '@/store/searchStore'
import { motion, useScroll, useTransform } from 'framer-motion'
import { mapApiError, type ApiError } from '@/services/errorMapper'

function isValidWebUrl(url: string) {
  return url.startsWith('http://') || url.startsWith('https://')
}

export function ResultsPage() {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const query = params.get('q') ?? ''
  const page = Number(params.get('page') ?? '1')
  const site = params.get('site') ?? ''
  const language = params.get('language') ?? ''
  const date_range = params.get('date_range') ?? ''

  const addToHistory = useSearchStore((s) => s.addToHistory)

  const { data, isLoading, isError, error, refetch } = useSearch({
    q: query,
    page,
    per_page: 10,
    site,
    language,
    date_range
  })

  const trackClick = useClickTracking(data?.query_context?.name ?? null)

  const { scrollY } = useScroll()
  const searchBarScale = useTransform(scrollY, [0, 100], [1, 0.95])
  const searchBarY = useTransform(scrollY, [0, 100], [0, -10])

  useEffect(() => {
    if (query) addToHistory(query)
  }, [query, addToHistory])

  function submit(q: string) {
    setParams({ q, page: '1', site, language, date_range })
  }

  function handleFilterChange(key: string, value: string) {
    setParams({ q: query, page: '1', site, language, date_range, [key]: value })
  }

  function gotoPage(p: number) {
    setParams({ q: query, page: String(p), site, language, date_range })
  }

  return (
    <div className="container-padded py-6 min-h-screen">
      <motion.div
        style={{ scale: searchBarScale, y: searchBarY }}
        className="sticky top-6 z-30 max-w-2xl mx-auto mb-8 transition-all duration-300"
      >
        <SearchInput
          value={query}
          onChange={(q) => setParams({ q, page: '1', site, language, date_range })}
          onSearch={() => submit(query)}
        />
      </motion.div>

      <FilterBar
        filters={{ site, language, date_range }}
        onFilterChange={handleFilterChange}
      />

      <div className="flex gap-8">
        <div className="flex-1 max-w-3xl space-y-6">
          {isLoading && (
            <div className="space-y-4" aria-busy="true">
              <AnswerBox isLoading />
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-6 w-2/3" />
                  <Skeleton className="h-4 w-full" />
                </div>
              ))}
            </div>
          )}

          {isError && (
            <div className="glass p-8 text-center rounded-3xl space-y-4">
              <Typography variant="p" className="text-slate-600 dark:text-slate-400">
                {error ? mapApiError(error as unknown as ApiError) : 'Something went wrong running that search.'}
              </Typography>
              <Button
                variant="primary"
                className="px-6 py-2"
                onClick={() => refetch()}
              >
                Try again
              </Button>
            </div>
          )}

          {data && !isLoading && (
            <>
              <Typography variant="small" className="text-slate-500 mb-4">
                {data.total_results.toLocaleString()} results
                {data.cache_hit && ' (cached)'} · {data.search_time_ms.toFixed(1)} ms
              </Typography>

              {data.total_results === 0 ? (
                <div className="glass p-12 text-center rounded-3xl space-y-6">
                  <Typography variant="h3" weight="bold">
                    No results for “{data.normalized_query}”
                  </Typography>
                  <Typography variant="p" align="center">
                    Try different keywords or remove filters.
                  </Typography>
                  <Button
                    variant="secondary"
                    className="px-6 py-2"
                    onClick={() => navigate('/')}
                  >
                    Back to search
                  </Button>
                </div>
              ) : (
                <div className="space-y-6">
                  <AnswerBox answer={data.answer} />

                  <div className="space-y-4">
                    {data.results
                      .filter(result => isValidWebUrl(result.url))
                      .map((result, i) => (
                      <ResultCard
                        key={result.id}
                        result={result}
                        position={(page - 1) * data.per_page + i + 1}
                        onSelect={trackClick}
                      />
                    ))}
                  </div>
                  <Pagination page={data.page} totalPages={data.total_pages} onPage={gotoPage} />
                </div>
              )}
            </>
          )}
        </div>

        <div className="hidden lg:block w-80">
          <KnowledgePanel
            data={data?.query_context ?? null}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  )
}
