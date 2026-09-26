import { Badge } from './Badge'
import { cn } from '@/lib/utils'

interface FilterChipProps {
  label: string
  isActive: boolean
  onClick: () => void
  variant?: 'default' | 'success' | 'error' | 'warning' | 'info'
}

export const FilterChip = ({ label, isActive, onClick, variant = 'default' }: FilterChipProps) => {
  return (
    <Badge
      variant={isActive ? 'info' : variant}
      className={cn(
        'cursor-pointer transition-all duration-200 select-none',
        isActive ? 'ring-2 ring-blue-500 ring-offset-2 dark:ring-offset-slate-900' : 'hover:bg-slate-200 dark:hover:bg-slate-700'
      )}
      onClick={onClick}
    >
      {label}
    </Badge>
  )
}
