import React from 'react'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  width?: 'full' | 'auto' | string
  height?: 'auto' | string
}

export const Skeleton = ({ className, width = 'full', height = 'auto', ...props }: SkeletonProps) => {
  const widthClass = width === 'full' ? 'w-full' : width === 'auto' ? 'w-auto' : `w-[${width}]`
  const heightClass = height === 'auto' ? 'h-auto' : `h-[${height}]`

  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-slate-200 dark:bg-slate-800',
        widthClass,
        heightClass,
        className
      )}
      {...props}
    />
  )
}
