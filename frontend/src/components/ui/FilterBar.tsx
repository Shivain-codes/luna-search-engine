import { FilterChip } from '@/components/ui/FilterChip'
import { Typography } from '@/components/ui/Typography'

interface FilterBarProps {
  filters: {
    site: string
    language: string
    date_range: string
  }
  onFilterChange: (key: string, value: string) => void
}

export const FilterBar = ({ filters, onFilterChange }: FilterBarProps) => {
  const filterOptions = {
    language: [
      { label: 'All Languages', value: '' },
      { label: 'English', value: 'en' },
      { label: 'Spanish', value: 'es' },
      { label: 'French', value: 'fr' },
      { label: 'German', value: 'de' },
    ],
    date_range: [
      { label: 'Any Time', value: '' },
      { label: 'Past Hour', value: '1h' },
      { label: 'Past 24h', value: '24h' },
      { label: 'Past Week', value: '7d' },
      { label: 'Past Month', value: '30d' },
      { label: 'Past Year', value: '1y' },
    ],
  }

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-3 py-4 border-b border-slate-200 dark:border-slate-800 mb-8">
      <div className="flex items-center gap-2">
        <Typography variant="small" weight="medium" className="text-slate-500 uppercase tracking-wider">
          Filters:
        </Typography>
      </div>

      <div className="flex items-center gap-2">
        <Typography variant="small" weight="medium" className="text-slate-500">Language:</Typography>
        <div className="flex gap-2">
          {filterOptions.language.map((opt) => (
            <FilterChip
              key={opt.value}
              label={opt.label}
              isActive={filters.language === opt.value}
              onClick={() => onFilterChange('language', opt.value)}
            />
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Typography variant="small" weight="medium" className="text-slate-500">Time:</Typography>
        <div className="flex gap-2">
          {filterOptions.date_range.map((opt) => (
            <FilterChip
              key={opt.value}
              label={opt.label}
              isActive={filters.date_range === opt.value}
              onClick={() => onFilterChange('date_range', opt.value)}
            />
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2 ml-auto">
        <Typography variant="small" weight="medium" className="text-slate-500">Site:</Typography>
        <input
          type="text"
          value={filters.site}
          onChange={(e) => onFilterChange('site', e.target.value)}
          placeholder="e.g. github.com"
          className="text-sm px-3 py-1 rounded-full border border-slate-200 dark:border-slate-800 bg-transparent focus:ring-2 focus:ring-blue-500 outline-none w-32 transition-all"
        />
      </div>
    </div>
  )
}
