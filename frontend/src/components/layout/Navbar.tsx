import { Link, useLocation } from 'react-router-dom'
import { Moon, Search, Sun } from 'lucide-react'
import { useThemeStore } from '@/store/themeStore'
import { motion } from 'framer-motion'

const tabs = [
  { to: '/', label: 'Search' },
  { to: '/how-it-works', label: 'How it Works' },
  { to: '/admin', label: 'Admin' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/settings', label: 'Settings' },
]

export function Navbar() {
  const location = useLocation()
  const { resolvedTheme, setTheme } = useThemeStore()

  return (
    <header className="glass sticky top-0 z-40 border-b border-primary-200 dark:border-primary-800">
      <nav className="container-padded flex items-center justify-between h-16" aria-label="Main">
        <Link to="/" className="flex items-center gap-2 font-sans font-bold text-xl tracking-tight transition-opacity hover:opacity-80">
          <div className="bg-accent-500 p-1.5 rounded-lg text-white">
            <Search className="h-5 w-5" aria-hidden="true" />
          </div>
          <span className="text-primary-900 dark:text-primary-50">Luna</span>
        </Link>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 mr-2">
            {tabs.map((tab) => {
              const active = location.pathname === tab.to
              return (
                <Link
                  key={tab.to}
                  to={tab.to}
                  className={`relative px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                    active
                      ? 'text-primary-900 dark:text-primary-50'
                      : 'text-primary-500 hover:text-primary-900 dark:text-primary-400 dark:hover:text-primary-50'
                  }`}
                  aria-current={active ? 'page' : undefined}
                >
                  {active && (
                    <motion.div
                      layoutId="nav-pill"
                      className="absolute inset-0 bg-accent-500/10 border border-accent-500/20 rounded-full"
                      transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                  <span className="relative z-10">{tab.label}</span>
                </Link>
              )
            })}
          </div>
          <button
            onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
            className="p-2.5 rounded-full hover:bg-primary-100 dark:hover:bg-primary-800 transition-colors focus-ring text-primary-600 dark:text-primary-400"
            aria-label="Toggle theme"
          >
            {resolvedTheme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
        </div>
      </nav>
    </header>
  )
}
