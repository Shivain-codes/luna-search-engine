import { Typography } from './Typography'
import { Badge } from './Badge'
import { Skeleton } from './Skeleton'
import { Sparkles } from 'lucide-react'

interface AnswerBoxProps {
  answer?: string | null
  isLoading?: boolean
}

export const AnswerBox = ({ answer, isLoading }: AnswerBoxProps) => {
  if (isLoading) {
    return (
      <div className="glass p-6 rounded-3xl space-y-3 w-full mb-8">
        <div className="flex items-center gap-2 mb-4">
          <div className="h-5 w-5 animate-pulse rounded-full bg-blue-500" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />
      </div>
    )
  }

  if (!answer) return null

  return (
    <div className="glass p-6 rounded-3xl space-y-4 w-full mb-8 border-l-4 border-l-blue-500 shadow-sm">
      <div className="flex items-center gap-2">
        <Sparkles size={18} className="text-blue-500" />
        <Badge variant="info">AI Summary</Badge>
      </div>
      <Typography variant="p" className="text-lg leading-relaxed font-medium">
        {answer}
      </Typography>
    </div>
  )
}
