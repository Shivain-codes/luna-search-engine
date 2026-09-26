import { useEffect } from 'react'
import { Route, Routes } from 'react-router-dom'
import { Navbar } from '@/components/layout/Navbar'
import { Footer } from '@/components/layout/Footer'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { Toaster } from '@/components/ui/Toaster'
import { SearchPage } from '@/pages/SearchPage'
import { ResultsPage } from '@/pages/ResultsPage'
import { LoginPage } from '@/pages/LoginPage'
import { AdminDashboard } from '@/pages/AdminDashboard'
import { AnalyticsDashboard } from '@/pages/AnalyticsDashboard'
import { SettingsPage } from '@/pages/SettingsPage'
import { HowItWorks } from '@/pages/HowItWorks'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { useThemeStore } from '@/store/themeStore'

// Simple DocsPage component since we don't have a separate file yet
function DocsPage() {
  return (
    <div className="max-w-4xl mx-auto py-10 px-6">
      <h1 className="text-4xl font-bold mb-4">Documentation</h1>
      <p className="text-lg text-muted-foreground">
        Welcome to the Luna Search Engine documentation. Learn how to crawl, index, and search.
      </p>
    </div>
  )
}

export default function App() {
  const initializeTheme = useThemeStore((s) => s.initializeTheme)

  useEffect(() => {
    initializeTheme()
  }, [initializeTheme])

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/search" element={<ResultsPage />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/docs" element={<DocsPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute>
                <AnalyticsDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          <Route path="/404" element={<NotFoundPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
      <Footer />
      <Toaster />
    </div>
  )
}
