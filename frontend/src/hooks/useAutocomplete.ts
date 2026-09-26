import { useState } from 'react'
import { useSuggest } from './useSearch'
import { useDebounce } from './useDebounce'
import type { Suggestion } from '@/types/search'

export function useAutocomplete(query: string, minLength = 2, limit = 10) {
  const debounced = useDebounce(query, 180)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [open, setOpen] = useState(false)

  const enabled = debounced.trim().length >= minLength
  const { data, isLoading } = useSuggest(enabled ? debounced : '', limit)
  const suggestions: Suggestion[] = data?.suggestions ?? []

  function reset() {
    setSelectedIndex(-1)
    setOpen(false)
  }

  return { suggestions, isLoading, selectedIndex, setSelectedIndex, open, setOpen, reset }
}
