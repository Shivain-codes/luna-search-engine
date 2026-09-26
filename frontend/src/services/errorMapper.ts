export interface ApiError {
  code: string
  message: string
  status: number
}

const ERROR_MAP: Record<string, string> = {
  'AUTH_REQUIRED': 'Please sign in to access this feature.',
  'INVALID_CREDENTIALS': 'The email or password provided is incorrect.',
  'RATE_LIMIT_EXCEEDED': 'Too many requests. Please wait a moment before trying again.',
  'INTERNAL_SERVER_ERROR': 'Our servers are experiencing a hiccup. Please try again shortly.',
  'NOT_FOUND': 'The requested resource could not be found.',
  'VALIDATION_ERROR': 'Some information provided was invalid. Please check your input.',
  'CRAWL_ALREADY_RUNNING': 'A crawl job is already in progress. Please wait for it to complete.',
  'CRAWL_NOT_FOUND': 'The specified crawl job could not be found.',
}

export function mapApiError(error: ApiError): string {
  return ERROR_MAP[error.code] || error.message || 'An unexpected error occurred. Please try again.'
}
