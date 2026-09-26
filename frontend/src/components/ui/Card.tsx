import type { HTMLAttributes } from 'react'

export function Card({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`card p-4 ${className}`} {...props} />
}

export function Badge({
  variant = 'primary',
  className = '',
  ...props
}: HTMLAttributes<HTMLSpanElement> & { variant?: 'primary' | 'success' | 'warning' | 'danger' }) {
  return <span className={`badge-${variant} ${className}`} {...props} />
}
