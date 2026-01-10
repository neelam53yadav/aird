/**
 * Authentication utility functions
 */

/**
 * Exchange NextAuth token with backend to get API access token
 * This function calls the internal API endpoint to exchange the NextAuth JWT
 * for a backend API access token, which is then stored as a cookie client-side
 * so JavaScript can read it for cross-origin API requests
 * 
 * @returns Promise<{success: boolean, token?: string}> - Returns success status and the token if available
 */
export async function exchangeToken(): Promise<{ success: boolean; token?: string }> {
  try {
    const response = await fetch('/api/internal/exchange', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      return { success: false }
    }

    const data = await response.json()
    
    // If token is returned, set it as a cookie client-side
    // This ensures JavaScript can read it for cross-origin requests
    if (data.ok && data.token) {
      // Set cookie client-side so JavaScript can read it
      const isProduction = typeof window !== 'undefined' && window.location.protocol === 'https:'
      const maxAge = 3600 // 1 hour
      
      // Set cookie with proper attributes
      document.cookie = `primedata_api_token=${encodeURIComponent(data.token)}; path=/; max-age=${maxAge}; ${isProduction ? 'secure; ' : ''}samesite=lax`
      
      return { success: true, token: data.token }
    }
    
    return { success: data.ok === true }
  } catch (error) {
    return { success: false }
  }
}








