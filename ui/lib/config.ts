/**
 * Centralized configuration for API URLs
 */

const DEFAULT_API_URL = "http://127.0.0.1:8000"

/**
 * Get the API base URL from environment variables or return the default
 * Uses 127.0.0.1 instead of localhost for better server-side compatibility
 * 
 * @returns The API base URL
 */
export function getApiUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_URL || 
    process.env.NEXT_PUBLIC_API_BASE || 
    process.env.API_URL ||
    DEFAULT_API_URL
  )
}

/**
 * Default API URL constant (for cases where you need the default value directly)
 */
export const DEFAULT_API_BASE_URL = DEFAULT_API_URL

