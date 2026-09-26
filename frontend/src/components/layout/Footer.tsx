export function Footer() {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 py-6 mt-12">
      <div className="container-padded flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-slate-500">
        <p>Luna — a search engine built from scratch.</p>
        <p className="font-mono">v0.1.0 · BM25 · PageRank</p>
      </div>
    </footer>
  )
}
