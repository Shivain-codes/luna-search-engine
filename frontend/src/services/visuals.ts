export const VisualService = {
  /**
   * Resolves a high-quality logo for a given domain.
   * Uses a fallback chain: Clearbit -> Google Favicon -> Generic Placeholder
   */
  getLogo: (domain: string): string => {
    if (!domain) return '/placeholder-logo.png'

    // Clean domain (remove http/https and paths)
    const cleanDomain = domain.replace(/^(https?:\/\/)?(www\.)?/, '').split('/')[0]

    // 1. Try Clearbit (Free for basic use, high quality)
    const clearbitUrl = `https://logo.clearbit.com/${cleanDomain}`

    // We return the Clearbit URL, but the component will handle the fallback if it 404s
    return clearbitUrl
  },

  /**
   * Resolves a representative image for an entity.
   * In a production app, this would call an Image Search API.
   */
  getEntityImage: (entityName: string, category?: string): string => {
    if (!entityName) return '/placeholder-entity.png'

    // Use a high-quality placeholder service (e.g., Source.unsplash or similar)
    // based on the category or entity name to avoid "grey boxes"
    const query = encodeURIComponent(category || entityName)
    return `https://source.unsplash.com/featured/?${query},technology`
  }
}
