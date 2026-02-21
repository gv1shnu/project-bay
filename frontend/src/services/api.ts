/**
 * services/api.ts — Centralized API client for all backend communication.
 *
 * Provides a singleton `apiService` that handles:
 *   - JWT token management (auto-inject Authorization header)
 *   - Request formatting (JSON and form-encoded)
 *   - Error handling (network errors, API errors)
 *   - Type-safe generic request method
 *
 * All API calls go through this service — components never call fetch() directly.
 */
import { User, Bet, Challenge, Notification } from '../types';

// API base URL from environment variables (set in frontend/.env)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Standard response shape for all API calls.
 * Either data or error will be populated, never both.
 */
interface ApiResponse<T> {
  data?: T;
  error?: string;
}


class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  /**
   * Get the stored JWT token from localStorage.
   * Returns null if user is not logged in.
   */
  private getToken(): string | null {
    return localStorage.getItem('token');
  }

  /**
   * Generic request method — all API calls go through this.
   *
   * Features:
   *   - Auto-adds Authorization header if JWT is available
   *   - Defaults to JSON content type
   *   - Returns { data } on success, { error } on failure
   *   - Handles network errors gracefully
   *
   * @param endpoint - API path (e.g., "/auth/login")
   * @param options - Standard fetch options (method, body, headers)
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const token = this.getToken();

    // Build headers — include auth token if available
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Default to JSON content type unless the caller specifies otherwise
    // (login uses application/x-www-form-urlencoded, so it overrides this)
    if (!options.headers || !(options.headers as Record<string, string>)['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          ...headers,
          ...(options.headers as Record<string, string>),
        },
      });

      // Handle non-OK responses (4xx, 5xx)
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        // Extract error message from backend response (usually in "detail" field)
        const errorMessage = errorData?.detail || `Error: ${response.status}`;
        return { error: typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage) };
      }

      // Parse successful response as JSON
      const data = await response.json();
      return { data };
    } catch {
      // Network error (server unreachable, CORS blocked, etc.)
      return { error: 'Network error. Please try again.' };
    }
  }


  // ════════════════════════════════════════════════════════
  // Auth Endpoints
  // ════════════════════════════════════════════════════════

  /** Register a new user. Backend creates account with 10 starting points. */
  async register(username: string, email: string, password: string): Promise<ApiResponse<User>> {
    return this.request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password }),
    });
  }

  /**
   * Login and get a JWT access token.
   * NOTE: Uses OAuth2 form format (application/x-www-form-urlencoded), not JSON.
   * This is required by FastAPI's OAuth2PasswordRequestForm on the backend.
   */
  async login(username: string, password: string): Promise<ApiResponse<{ access_token: string; token_type: string }>> {
    // Build form-encoded body (not JSON!) — OAuth2 convention
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    return this.request('/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });
  }

  /** Fetch current user's profile using the stored JWT. */
  async getCurrentUser(): Promise<ApiResponse<User>> {
    return this.request<User>('/auth/me');
  }

  /** Fetch any user's public profile by username. */
  async getUserProfile(username: string): Promise<ApiResponse<User>> {
    return this.request<User>(`/auth/user/${username}`);
  }

  /** Get total registered user count (shown in homepage footer). */
  async getUserCount(): Promise<ApiResponse<{ count: number }>> {
    return this.request<{ count: number }>('/auth/stats/count');
  }


  // ════════════════════════════════════════════════════════
  // Bet Endpoints
  // ════════════════════════════════════════════════════════

  /**
   * Fetch all public bets for the homepage feed.
   * Returns bets with creator usernames and non-rejected challenges.
   * The backend wraps results in a PaginatedResponse — we extract items.
   */
  async getPublicBets(): Promise<ApiResponse<Bet[]>> {
    // Request the paginated response, then unwrap the items array
    const response = await this.request<{ items: Bet[] }>('/bets/public?limit=100');
    if (response.data) {
      return { data: response.data.items };  // Unwrap pagination wrapper
    }
    return { error: response.error };
  }

  /** Fetch current user's own bets (requires auth). */
  async getBets(): Promise<ApiResponse<Bet[]>> {
    const response = await this.request<{ items: Bet[] }>('/bets/?limit=100');
    if (response.data) {
      return { data: response.data.items };
    }
    return { error: response.error };
  }

  /** Create a new bet with the given stake amount (deducts points from creator). */
  async createBet(
    title: string,
    criteria: string,
    amount: number,
    deadline: string
  ): Promise<ApiResponse<Bet>> {
    return this.request<Bet>('/bets/', {
      method: 'POST',
      body: JSON.stringify({ title, criteria, amount, deadline }),
    });
  }

  /** Challenge a bet — stake points betting the creator will fail. */
  async challengeBet(betId: number, amount: number): Promise<ApiResponse<Challenge>> {
    return this.request<Challenge>(`/bets/${betId}/challenge`, {
      method: 'POST',
      body: JSON.stringify({ amount }),
    });
  }

  /** Update a bet's status (won/lost/cancelled). Only the creator can do this. */
  async updateBetStatus(betId: number, status: string): Promise<ApiResponse<Bet>> {
    return this.request<Bet>(`/bets/${betId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }

  /** Toggle star on a bet — stars if not starred, unstars if already starred. Requires auth. */
  async starBet(betId: number): Promise<ApiResponse<{ id: number; stars: number; starred: boolean }>> {
    return this.request<{ id: number; stars: number; starred: boolean }>(`/bets/${betId}/star`, {
      method: 'POST',
    });
  }

  /** Upload proof of bet completion (comment + media file). Creator only. */
  async submitProof(
    betId: number,
    comment: string,
    file: File
  ): Promise<ApiResponse<{ id: number; status: string; proof_comment: string; proof_media_url: string }>> {
    const formData = new FormData();
    formData.append('comment', comment);
    formData.append('file', file);

    const token = localStorage.getItem('token');
    try {
      const response = await fetch(`${this.baseUrl}/bets/${betId}/proof`, {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => undefined);
        return { error: errData?.detail || `Upload failed (${response.status})` };
      }

      const data = await response.json();
      return { data };
    } catch (err: any) {
      return { error: err.message || 'Network error' };
    }
  }


  // ════════════════════════════════════════════════════════
  // Challenge Endpoints
  // ════════════════════════════════════════════════════════

  /** Accept a challenge on your bet (matches the challenger's stake). */
  async acceptChallenge(betId: number, challengeId: number): Promise<ApiResponse<Challenge>> {
    return this.request<Challenge>(`/bets/${betId}/challenges/${challengeId}/accept`, {
      method: 'POST',
    });
  }

  /** Reject a challenge on your bet (refunds the challenger). */
  async rejectChallenge(betId: number, challengeId: number): Promise<ApiResponse<Challenge>> {
    return this.request<Challenge>(`/bets/${betId}/challenges/${challengeId}/reject`, {
      method: 'POST',
    });
  }

  /** Withdraw a challenge you made (refunds stakes). */
  async withdrawChallenge(betId: number, challengeId: number): Promise<ApiResponse<Challenge>> {
    return this.request<Challenge>(`/bets/${betId}/challenges/${challengeId}/withdraw`, {
      method: 'POST',
    });
  }

  // ════════════════════════════════════════════════════════
  // Admin Endpoints (passphrase-protected)
  // ════════════════════════════════════════════════════════

  /** Verify the admin passphrase before showing the dashboard. */
  async verifyAdminPassphrase(passphrase: string): Promise<ApiResponse<{ status: string }>> {
    return this.request<{ status: string }>('/admin/verify', {
      method: 'POST',
      headers: { 'X-Admin-Passphrase': passphrase },
    });
  }

  /** Fetch all users for the admin dashboard. */
  async getAdminUsers(passphrase: string): Promise<ApiResponse<User[]>> {
    return this.request<User[]>('/admin/users', {
      headers: { 'X-Admin-Passphrase': passphrase },
    });
  }

  /** Fetch all bets with challenges for the admin dashboard. */
  async getAdminBets(passphrase: string): Promise<ApiResponse<Bet[]>> {
    return this.request<Bet[]>('/admin/bets', {
      headers: { 'X-Admin-Passphrase': passphrase },
    });
  }


  // ════════════════════════════════════════════════════════
  // Notification Endpoints
  // ════════════════════════════════════════════════════════

  /** Get all notifications for the current user (newest first). */
  async getNotifications(): Promise<ApiResponse<Notification[]>> {
    return this.request<Notification[]>('/notifications/');
  }

  /** Get unread notification count (for the bell badge). */
  async getUnreadCount(): Promise<ApiResponse<{ count: number }>> {
    return this.request<{ count: number }>('/notifications/unread');
  }

  /** Mark a single notification as read. */
  async markNotificationRead(id: number): Promise<ApiResponse<{ id: number; is_read: number }>> {
    return this.request<{ id: number; is_read: number }>(`/notifications/${id}/read`, {
      method: 'POST',
    });
  }

  /** Mark all notifications as read. */
  async markAllNotificationsRead(): Promise<ApiResponse<{ status: string }>> {
    return this.request<{ status: string }>('/notifications/read-all', {
      method: 'POST',
    });
  }


  // ════════════════════════════════════════════════════════
  // Proof Vote Endpoints
  // ════════════════════════════════════════════════════════

  /** Vote on proof: 'cool' (approve) or 'not_cool' (reject). */
  async voteOnProof(betId: number, vote: 'cool' | 'not_cool'): Promise<ApiResponse<{
    id: number; bet_id: number; vote: string;
    cool_count: number; total_voters: number; votes_cast: number; bet_status: string;
  }>> {
    return this.request(`/bets/${betId}/vote?vote=${vote}`, {
      method: 'POST',
    });
  }
}

// Singleton instance — import this anywhere as `apiService`
export const apiService = new ApiService();
