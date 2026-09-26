import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import type { SearchParams } from '@/types/search'

export function useSearch(params: SearchParams) {
  return useQuery({
    queryKey: ['search', params],
    queryFn: () => api.search(params),
    enabled: !!params.q && params.q.trim().length > 0,
    staleTime: 1000 * 60 * 2,
  })
}

export function useSuggest(query: string, limit = 10) {
  return useQuery({
    queryKey: ['suggest', query, limit],
    queryFn: () => api.suggest(query, limit),
    enabled: !!query && query.trim().length >= 2,
    staleTime: 1000 * 60 * 5,
  })
}
