import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SearchState {
  searchHistory: string[]
  addToHistory: (query: string) => void
  clearHistory: () => void
}

export const useSearchStore = create<SearchState>()(
  persist(
    (set) => ({
      searchHistory: [],
      addToHistory: (query: string) =>
        set((state) => ({
          searchHistory: [query, ...state.searchHistory.filter((q) => q !== query)].slice(0, 10),
        })),
      clearHistory: () => set({ searchHistory: [] }),
    }),
    {
      name: 'luna-search-history',
    }
  )
)
