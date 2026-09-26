import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '@/services/api'
import { Card } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card className="flex-1">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-2xl font-semibold font-mono mt-1">{value}</p>
    </Card>
  )
}

export function AnalyticsDashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => api.queryAnalytics(),
  })

  if (isLoading) {
    return (
      <div className="container-padded py-12 flex justify-center">
        <Spinner className="h-8 w-8 text-primary-600" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="container-padded py-12">
        <Card className="text-center py-8">Analytics are unavailable right now.</Card>
      </div>
    )
  }

  const ctr = data.click_through_rate
  return (
    <div className="container-padded py-6">
      <h1 className="text-2xl font-semibold mb-6">Analytics</h1>

      <div className="flex flex-col sm:flex-row gap-4 mb-8">
        <Metric label="Total queries" value={data.total_queries.toLocaleString()} />
        <Metric label="Click-through rate" value={ctr === null ? '—' : `${(ctr * 100).toFixed(1)}%`} />
        <Metric label="p95 latency" value={data.latency.p95 === null ? '—' : `${data.latency.p95.toFixed(1)} ms`} />
        <Metric label="p99 latency" value={data.latency.p99 === null ? '—' : `${data.latency.p99.toFixed(1)} ms`} />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <h2 className="font-medium mb-3">Top queries</h2>
          {data.top_queries.length === 0 ? (
            <p className="text-slate-500 text-sm">No query data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.top_queries}>
                <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                <XAxis dataKey="query" tick={{ fontSize: 11 }} interval={0} angle={-20} height={50} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card>
          <h2 className="font-medium mb-3">Zero-result queries</h2>
          {data.zero_result_queries.length === 0 ? (
            <p className="text-slate-500 text-sm">No zero-result queries.</p>
          ) : (
            <ul className="divide-y divide-slate-200 dark:divide-slate-700">
              {data.zero_result_queries.map((z) => (
                <li key={z.query} className="flex justify-between py-2 text-sm">
                  <span>{z.query}</span>
                  <span className="font-mono text-slate-400">{z.count}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
