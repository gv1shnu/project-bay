const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

interface ApiResponse<T> {
  data?: T
  error?: string
}

class ApiService {
  private getToken(): string | null {
    return localStorage.getItem('token')
  }

  private setToken(token: string): void {
    localStorage.setItem('token', token)
  }

  private removeToken(): void {
    localStorage.removeItem('token')
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const token = this.getToken()
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (token) {
      (headers as any)['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      })

      const data = await response.json()

      if (!response.ok) {
        return {
          error: data.detail || `Error: ${response.statusText}`,
        }
      }

      return { data }
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error occurred',
      }
    }
  }

  // Auth endpoints
  async register(username: string, email: string, password: string) {
    const response = await this.request<{
      id: number
      username: string
      email: string
      points: number
      created_at: string
    }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password }),
    })

    if (response.data) {
      // After registration, we need to login to get the token
      // The backend doesn't return a token on registration, so we login
      return this.login(username, password)
    }

    return response
  }

  async login(username: string, password: string) {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    const headers: HeadersInit = {
      'Content-Type': 'application/x-www-form-urlencoded',
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers,
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        return {
          error: data.detail || `Error: ${response.statusText}`,
        }
      }

      if (data.access_token) {
        this.setToken(data.access_token)
      }

      return { data }
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error occurred',
      }
    }
  }

  async getCurrentUser() {
    return this.request<{
      id: number
      username: string
      email: string
      points: number
      created_at: string
    }>('/auth/me')
  }

  async getUserProfile(username: string) {
    return this.request<{
      id: number
      username: string
      email: string
      points: number
      created_at: string
    }>(`/auth/user/${username}`)
  }

  logout() {
    this.removeToken()
  }

  async getUserCount() {
    return this.request<{ count: number }>('/auth/stats/count')
  }

  // Bet endpoints
  async getPublicBets() {
    // Public endpoint - no authentication required
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }

    try {
      const response = await fetch(`${API_BASE_URL}/bets/public`, {
        method: 'GET',
        headers,
      })

      const data = await response.json()

      if (!response.ok) {
        return {
          error: data.detail || `Error: ${response.statusText}`,
        }
      }

      // Handle paginated response - extract items array
      return { data: data.items || data }
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error occurred',
      }
    }
  }

  async getBets() {
    return this.request<
      Array<{
        id: number
        user_id: number
        amount: number
        description: string | null
        status: 'active' | 'won' | 'lost' | 'cancelled'
        created_at: string
        updated_at: string | null
      }>
    >('/bets/')
  }

  async getBet(betId: number) {
    return this.request<{
      id: number
      user_id: number
      amount: number
      description: string | null
      status: 'active' | 'won' | 'lost' | 'cancelled'
      created_at: string
      updated_at: string | null
    }>(`/bets/${betId}`)
  }

  async createBet(title: string, criteria: string, amount: number, deadline: string) {
    return this.request<{
      id: number
      user_id: number
      title: string
      amount: number
      criteria: string
      deadline: string
      status: 'active' | 'won' | 'lost' | 'cancelled'
      created_at: string
      updated_at: string | null
    }>('/bets/', {
      method: 'POST',
      body: JSON.stringify({ title, criteria, amount, deadline }),
    })
  }

  async challengeBet(betId: number, amount: number) {
    return this.request<{
      id: number
      bet_id: number
      challenger_id: number
      challenger_username: string
      amount: number
      status: 'pending' | 'accepted' | 'rejected'
      created_at: string
    }>(`/bets/${betId}/challenge`, {
      method: 'POST',
      body: JSON.stringify({ amount }),
    })
  }

  async updateBetStatus(betId: number, status: 'active' | 'won' | 'lost' | 'cancelled') {
    return this.request<{
      id: number
      user_id: number
      amount: number
      description: string | null
      status: 'active' | 'won' | 'lost' | 'cancelled'
      created_at: string
      updated_at: string | null
    }>(`/bets/${betId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    })
  }
}

export const apiService = new ApiService()

