import { create } from 'zustand'

export interface Toast {
  id: number
  message: string
  variant: 'info' | 'success' | 'error'
}

interface ToastState {
  toasts: Toast[]
  push: (message: string, variant?: Toast['variant']) => void
  dismiss: (id: number) => void
}

let nextId = 1

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (message, variant = 'info') => {
    const id = nextId++
    set((s) => ({ toasts: [...s.toasts, { id, message, variant }] }))
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 4000)
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))

export function toast(message: string, variant?: Toast['variant']) {
  useToastStore.getState().push(message, variant)
}

const styles: Record<Toast['variant'], string> = {
  info: 'bg-slate-800 text-white',
  success: 'bg-green-600 text-white',
  error: 'bg-red-600 text-white',
}

export function Toaster() {
  const { toasts, dismiss } = useToastStore()
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2" aria-live="polite">
      {toasts.map((t) => (
        <button
          key={t.id}
          onClick={() => dismiss(t.id)}
          className={`rounded-lg px-4 py-2 text-sm shadow-lg animate-slide-up ${styles[t.variant]}`}
        >
          {t.message}
        </button>
      ))}
    </div>
  )
}
