import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="container-padded flex flex-col items-center justify-center min-h-[70vh] text-center">
      <p className="font-mono text-6xl font-bold text-primary-600">404</p>
      <p className="text-slate-500 mt-2 mb-6">That page could not be found.</p>
      <Link to="/" className="btn-primary">
        Back to search
      </Link>
    </div>
  )
}
