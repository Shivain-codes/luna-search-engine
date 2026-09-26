import React from 'react'
import { Typography } from '@/components/ui/Typography'
import { motion } from 'framer-motion'
import { Search, Database, Zap, Globe, Cpu } from 'lucide-react'

const Step = ({ icon: Icon, title, description, details }: { icon: any, title: string, description: string, details: string[] }) => (
  <motion.div
    initial={{ opacity: 0, x: -20 }}
    whileInView={{ opacity: 1, x: 0 }}
    viewport={{ once: true }}
    className="glass p-6 rounded-3xl space-y-4 border border-primary-200 dark:border-primary-800"
  >
    <div className="h-12 w-12 rounded-2xl bg-accent-500/10 text-accent-500 flex items-center justify-center">
      <Icon size={24} />
    </div>
    <Typography variant="h4" weight="bold">{title}</Typography>
    <Typography variant="p" className="text-slate-600 dark:text-slate-400">
      {description}
    </Typography>
    <ul className="space-y-2">
      {details.map((detail, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-slate-500 dark:text-slate-400">
          <span className="text-accent-500 mt-1">•</span>
          {detail}
        </li>
      ))}
    </ul>
  </motion.div>
)

export function HowItWorks() {
  return (
    <div className="container-padded py-12 space-y-16">
      <div className="text-center space-y-4 max-w-3xl mx-auto">
        <Typography variant="h1" weight="bold" className="text-5xl md:text-7xl tracking-tighter">
          How Luna Works
        </Typography>
        <Typography variant="p" align="center" className="text-lg md:text-xl text-slate-500 dark:text-slate-400">
          A deep dive into the Information Retrieval (IR) pipeline, from raw HTML to ranked search results.
        </Typography>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
        <Step
          icon={Globe}
          title="1. Distributed Crawling"
          description="The crawler discovers the web by following links and respecting robots.txt."
          details={[
            "Polite crawling with per-domain rate limiting",
            "Recursive frontier management using a priority queue",
            "Content deduplication via SHA-256 hashing",
            "Metadata extraction (titles, headings, descriptions)"
          ]}
        />
        <Step
          icon={Database}
          title="2. Inverted Indexing"
          description="Raw content is transformed into a searchable mathematical structure."
          details={[
            "Tokenization and stemming of text fields",
            "Positional postings lists for phrase search support",
            "Global term statistics (DF, TF) for scoring",
            "Asynchronous indexing pipeline via RabbitMQ"
          ]}
        />
        <Step
          icon={Cpu}
          title="3. Ranking Engine"
          description="Results are scored using a blend of local relevance and global authority."
          details={[
            "BM25 (Best Matching 25) for keyword relevance",
            "PageRank algorithm for link-based authority",
            "Field-weighted scoring (Title > Headings > Body)",
            "Freshness decay for time-sensitive content"
          ]}
        />
        <Step
          icon={Zap}
          title="4. Serving & RAG"
          description="Queries are processed in milliseconds and enhanced with AI."
           details={[
            "Sub-millisecond retrieval via optimized SQL queries",
            "Redis caching for high-frequency queries",
            "RAG (Retrieval-Augmented Generation) for AI summaries",
            "Query normalization and autocomplete suggestions"
          ]}
        />
      </div>

      <div className="glass p-8 rounded-3xl border border-primary-200 dark:border-primary-800 max-w-4xl mx-auto">
        <Typography variant="h3" weight="bold" className="mb-4">The Tech Stack</Typography>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Backend', value: 'FastAPI / Python 3.13' },
            { label: 'Database', value: 'PostgreSQL / SQLAlchemy' },
            { label: 'Cache', value: 'Redis' },
            { label: 'Messaging', value: 'RabbitMQ' },
            { label: 'Frontend', value: 'React / TypeScript' },
            { label: 'Styling', value: 'Tailwind CSS' },
            { label: 'State', value: 'Zustand / React Query' },
            { label: 'IR Core', value: 'BM25 + PageRank' },
          ].map((item, i) => (
            <div key={i} className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800/50">
              <Typography variant="small" weight="medium" className="text-slate-500 uppercase">{item.label}</Typography>
              <Typography variant="p" weight="semibold">{item.value}</Typography>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
