/**
 * Authentication utility functions
 */

/**
 * Exchange NextAuth token with backend to get API access token
 * This function calls the internal API endpoint to exchange the NextAuth JWT
 * for a backend API access token, which is then stored as an httpOnly cookie
 * 
 * @returns Promise<boolean> - Returns true if exchange was successful, false otherwise
 */
export async function exchangeToken(): Promise<boolean> {
  try {
    const response = await fetch('/api/internal/exchange', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      console.error('Token exchange failed:', response.status, response.statusText)
      return false
    }

    const data = await response.json()
    return data.ok === true
  } catch (error) {
    console.error('Token exchange error:', error)
    return false
  }
}






