import { Input } from './Input'
import { Button } from './Button'
import { Search, X } from 'lucide-react'

interface SearchInputProps {
  value: string
  onChange: (value: string) => void
  onSearch: () => void
  placeholder?: string
  isLoading?: boolean
}

export const SearchInput = ({
  value,
  onChange,
  onSearch,
  placeholder = 'Search the web...',
  isLoading,
}: SearchInputProps) => {
  return (
    <div className="relative group w-full max-w-2xl mx-auto">
      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors">
        <Search size={18} />
      </div>

      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pl-11 pr-12 h-12 text-base shadow-sm transition-all duration-200 focus:shadow-md"
        onKeyDown={(e) => e.key === 'Enter' && onSearch()}
      />

      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-12 top-1/2 -translate-y-1/2 p-1 rounded-full text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <X size={14} />
        </button>
      )}

      <Button
        onClick={onSearch}
        isLoading={isLoading}
        className="absolute right-2 top-1/2 -translate-y-1/2 h-8 px-4 text-sm"
      >
        Search
      </Button>
    </div>
  )
}
