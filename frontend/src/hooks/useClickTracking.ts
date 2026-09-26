import { useCallback } from 'react'
import { api } from '@/services/api'

export function useClickTracking(queryContext: string | null) {
  return useCallback(
    (documentId: string, position: number) => {
      if (!queryContext) return
      // Fire and forget: click logging must never block navigation.
      api.trackClick({ query_context: queryContext, document_id: documentId, position }).catch(() => {
        /* non-blocking */
      })
    },
    [queryContext]
  )
}
