import React from 'react'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

interface TypographyProps extends React.HTMLAttributes<HTMLElement> {
  variant?: 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'small' | 'muted'
  weight?: 'light' | 'regular' | 'medium' | 'semibold' | 'bold'
  align?: 'left' | 'center' | 'right'
}

export const Typography = React.forwardRef<any, TypographyProps>(
  ({ className, variant = 'p', weight = 'regular', align = 'left', children, ...props }, ref) => {
    const variants = {
      h1: 'text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50',
      h2: 'text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50',
      h3: 'text-xl font-semibold text-slate-900 dark:text-slate-50',
      h4: 'text-lg font-medium text-slate-900 dark:text-slate-50',
      p: 'text-base text-slate-600 dark:text-slate-400 leading-relaxed',
      small: 'text-sm text-slate-500 dark:text-slate-500',
      muted: 'text-sm text-slate-400 dark:text-slate-600',
    }

    const weights = {
      light: 'font-light',
      regular: 'font-normal',
      medium: 'font-medium',
      semibold: 'font-semibold',
      bold: 'font-bold',
    }

    const aligns = {
      left: 'text-left',
      center: 'text-center',
      right: 'text-right',
    }

    const Component = variant === 'h1' ? 'h1' : variant === 'h2' ? 'h2' : variant === 'h3' ? 'h3' : variant === 'h4' ? 'h4' : 'p'

    return (
      <Component
        ref={ref}
        className={cn(
          variants[variant],
          weights[weight],
          aligns[align],
          className
        )}
        {...props}
      >
        {children}
      </Component>
    )
  }
)

Typography.displayName = 'Typography'
