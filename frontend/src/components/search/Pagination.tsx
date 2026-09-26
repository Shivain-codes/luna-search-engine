interface Props {
  page: number
  totalPages: number
  onPage: (page: number) => void
}

export function Pagination({ page, totalPages, onPage }: Props) {
  if (totalPages <= 1) return null
  const start = Math.max(1, page - 2)
  const end = Math.min(totalPages, start + 4)
  const pages = []
  for (let p = start; p <= end; p++) pages.push(p)

  return (
    <nav className="flex items-center justify-center gap-1 mt-6" aria-label="Pagination">
      <button
        className="btn-ghost px-3 py-1.5"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
        aria-label="Previous page"
      >
        Prev
      </button>
      {pages.map((p) => (
        <button
          key={p}
          onClick={() => onPage(p)}
          aria-current={p === page ? 'page' : undefined}
          className={`px-3 py-1.5 rounded-lg text-sm ${
            p === page ? 'bg-primary-600 text-white' : 'hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          {p}
        </button>
      ))}
      <button
        className="btn-ghost px-3 py-1.5"
        disabled={page >= totalPages}
        onClick={() => onPage(page + 1)}
        aria-label="Next page"
      >
        Next
      </button>
    </nav>
  )
}
