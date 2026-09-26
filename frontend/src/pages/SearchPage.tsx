import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AuroraBackground } from '@/components/ui/aurora-background'
import { SearchInput } from '@/components/ui/SearchInput'
import { Typography } from '@/components/ui/Typography'

export function SearchPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  function handleSearch() {
    if (!query.trim()) return
    navigate(`/search?q=${encodeURIComponent(query.trim())}`)
  }

  return (
    <AuroraBackground>
      <div className="relative flex flex-col items-center justify-center min-h-screen px-4 z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.8,
            ease: [0.16, 1, 0.3, 1],
          }}
          className="flex flex-col items-center gap-12 w-full max-w-4xl"
        >
          <div className="text-center space-y-4">
            <Typography
              variant="h1"
              className="text-6xl md:text-8xl font-bold tracking-tighter"
            >
              Luna
            </Typography>
            <Typography
              variant="p"
              align="center"
              className="text-lg md:text-xl font-light max-w-xl mx-auto"
            >
              Fast, private, and production-ready search.
            </Typography>
          </div>

          <div className="w-full max-w-2xl">
            <SearchInput
              value={query}
              onChange={setQuery}
              onSearch={handleSearch}
              placeholder="Search the web..."
            />
          </div>
        </motion.div>
      </div>
    </AuroraBackground>
  )
}
