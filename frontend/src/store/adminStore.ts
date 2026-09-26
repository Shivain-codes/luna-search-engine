import { create } from 'zustand'
import { CrawlJob } from '@/types/admin'

interface AdminState {
  sidebarOpen: boolean
  selectedJob: CrawlJob | null
  setSidebarOpen: (open: boolean) => void
  toggleSidebar: () => void
  setSelectedJob: (job: CrawlJob | null) => void
}

export const useAdminStore = create<AdminState>((set) => ({
  sidebarOpen: true,
  selectedJob: null,

  setSidebarOpen: (open: boolean) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSelectedJob: (job: CrawlJob | null) => set({ selectedJob: job }),
}))