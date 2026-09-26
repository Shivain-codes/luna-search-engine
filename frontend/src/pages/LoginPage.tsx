import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Typography } from '@/components/ui/Typography'
import { useAuthStore } from '@/store/authStore'
import { toast } from '@/components/ui/Toaster'
import { motion } from 'framer-motion'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: string } }
  const login = useAuthStore((s) => s.login)
  const [email, setEmail] = useState('admin@luna.dev')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await login(email, password)
      toast('Signed in', 'success')
      navigate(location.state?.from ?? '/admin', { replace: true })
    } catch (err: any) {
      toast(err.message || 'Invalid credentials', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container-padded flex items-center justify-center min-h-screen">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass p-8 w-full max-w-sm space-y-6 shadow-xl"
      >
        <div className="text-center space-y-2">
          <Typography variant="h3" weight="bold">Admin Sign In</Typography>
          <Typography variant="muted" align="center">
            Enter your credentials to access the observability plane
          </Typography>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Typography variant="small" weight="medium">Email</Typography>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="admin@luna.dev"
            />
          </div>
          <div className="space-y-2">
            <Typography variant="small" weight="medium">Password</Typography>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </div>
          <Button type="submit" isLoading={loading} className="w-full py-6 text-base">
            Sign In
          </Button>
        </form>

        <div className="pt-4 border-t border-slate-200 dark:border-slate-800">
          <Typography variant="muted" align="center" className="text-xs">
            Development default: admin@luna.dev
          </Typography>
        </div>
      </motion.div>
    </div>
  )
}
