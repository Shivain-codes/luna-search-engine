import { useEffect, useRef, useState } from 'react'
import { Search } from 'lucide-react'
import { useAutocomplete } from '@/hooks/useAutocomplete'
import { motion, AnimatePresence } from 'framer-motion'

interface Props {
  initialValue?: string
  onSubmit: (query: string) => void
  autoFocus?: boolean
}

export function SearchBox({ initialValue = '', onSubmit, autoFocus }: Props) {
  const [value, setValue] = useState(initialValue)
  const { suggestions, selectedIndex, setSelectedIndex, open, setOpen, reset } =
    useAutocomplete(value)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => setValue(initialValue), [initialValue])

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) reset()
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [reset])

  function submit(q: string) {
    const trimmed = q.trim()
    if (!trimmed) return
    reset()
    onSubmit(trimmed)
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || suggestions.length === 0) {
      if (e.key === 'Enter') submit(value)
      return
    }
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(Math.min(selectedIndex + 1, suggestions.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(Math.max(selectedIndex - 1, -1))
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0) {
          const chosen = suggestions[selectedIndex].text
          setValue(chosen)
          submit(chosen)
        } else {
          submit(value)
        }
        break
      case 'Escape':
        reset()
        break
    }
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <motion.div
        initial={false}
        whileFocus={{ scale: 1.01 }}
        className="relative group"
      >
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-primary-400 group-focus-within:text-accent-500 transition-colors">
          <Search className="h-5 w-5" aria-hidden="true" />
        </div>
        <input
          type="search"
          role="combobox"
          aria-expanded={open}
          aria-controls="search-suggestions"
          aria-label="Search query"
          autoFocus={autoFocus}
          value={value}
          placeholder="Search the web..."
          onChange={(e) => {
            setValue(e.target.value)
            setOpen(true)
            setSelectedIndex(-1)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          className="w-full pl-12 py-3 text-lg bg-white/50 dark:bg-black/50 backdrop-blur-sm border border-primary-200 dark:border-primary-800 rounded-2xl focus:ring-2 focus:ring-accent-500/50 outline-none transition-all duration-200 placeholder:text-primary-400 text-primary-900 dark:text-primary-50"
        />
      </motion.div>
      <AnimatePresence>
        {open && suggestions.length > 0 && (
          <motion.ul
            initial={{ opacity: 0, y: -10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.98 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            id="search-suggestions"
            role="listbox"
            className="absolute z-20 mt-2 w-full glass overflow-hidden py-2 shadow-2xl rounded-2xl border border-primary-200 dark:border-primary-800"
          >
            {suggestions.map((s, i) => (
              <li
                key={`${s.text}-${i}`}
                role="option"
                aria-selected={i === selectedIndex}
                className={`px-4 py-3 cursor-pointer flex items-center justify-between transition-colors ${
                  i === selectedIndex
                    ? 'bg-accent-500/10 text-accent-600 dark:text-accent-400'
                    : 'text-primary-700 dark:text-primary-300 hover:bg-primary-100 dark:hover:bg-primary-900'
                }`}
                onMouseEnter={() => setSelectedIndex(i)}
                onMouseDown={(e) => {
                  e.preventDefault()
                  setValue(s.text)
                  submit(s.text)
                }}
              >
                <span className="font-medium">{s.text}</span>
                <span className="text-xs text-primary-400 font-mono opacity-60">{s.type}</span>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  )
}
