import { Typography } from './Typography'
import { cn } from '@/lib/utils'

interface StatTileProps {
  label: string
  value: string | number
  description?: string
  trend?: 'up' | 'down' | 'neutral'
}

export const StatTile = ({ label, value, description, trend }: StatTileProps) => {
  return (
    <div className="glass p-6 rounded-3xl flex flex-col gap-1 transition-all duration-200 hover:shadow-md">
      <Typography variant="small" weight="medium" className="text-slate-500 uppercase tracking-wider">
        {label}
      </Typography>
      <Typography variant="h2" weight="bold" className="font-mono">
        {value}
      </Typography>
      {description && (
        <Typography variant="muted" className="text-xs">
          {description}
        </Typography>
      )}
      {trend && (
        <div className={cn(
          'text-xs font-medium mt-2',
          trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-slate-500'
        )}>
          {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {trend}
        </div>
      )}
    </div>
  )
}
