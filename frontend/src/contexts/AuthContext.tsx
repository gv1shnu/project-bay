/**
 * contexts/AuthContext.tsx — Global authentication state management.
 *
 * Provides auth state and actions to the entire app via React Context:
 *   - user: The current user's data (or null if not logged in)
 *   - login(username, password): Authenticate and store JWT
 *   - signup(username, email, password): Register and auto-login
 *   - logout(): Clear JWT and user state
 *   - refreshUser(): Re-fetch user data from the server
 *   - isAuthenticated: Boolean shortcut for checking login status
 *   - loading: True while checking stored token on first load
 *
 * JWT tokens are stored in localStorage and automatically injected
 * into API requests by the ApiService.
 */
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '../types';
import { apiService } from '../services/api';

// Shape of the context value — everything consumers can access
interface AuthContextType {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  signup: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  loading: boolean;
  refreshUser: () => Promise<void>;
}

// Create the context with null default (will be provided by AuthProvider)
const AuthContext = createContext<AuthContextType | null>(null);


/**
 * AuthProvider — Wrap your app in this to make auth state available everywhere.
 * Usage: <AuthProvider><App /></AuthProvider>
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);  // True until initial token check completes

  /**
   * On mount: check localStorage for an existing JWT token.
   * If found, validate it by calling GET /auth/me.
   * If the token is expired or invalid, silently clear it.
   */
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        // Token exists — try to hydrate user state
        const { data, error } = await apiService.getCurrentUser();
        if (data && !error) {
          setUser(data);  // Token is valid — user is logged in
        } else {
          // Token is expired or invalid — clean up
          localStorage.removeItem('token');
        }
      }
      setLoading(false);  // Done checking — app can render
    };
    initAuth();
  }, []);

  /**
   * Re-fetch the current user's data from the server.
   * Call this after actions that change user state (e.g., creating a bet deducts points).
   */
  const refreshUser = async () => {
    const { data, error } = await apiService.getCurrentUser();
    if (data && !error) {
      setUser(data);
    }
  };

  /**
   * Login: authenticate with the backend, store the JWT, and fetch user data.
   * Throws an error string if login fails (caught by the LoginPage component).
   */
  const login = async (username: string, password: string) => {
    const { data, error } = await apiService.login(username, password);
    if (error || !data) {
      throw new Error(error || 'Login failed');
    }
    // Store JWT in localStorage — persists across page reloads
    localStorage.setItem('token', data.access_token);
    // Fetch full user data now that we have a valid token
    await refreshUser();
  };

  /**
   * Signup: register a new account, then auto-login.
   * The backend creates the user with 10 starting points.
   */
  const signup = async (username: string, email: string, password: string) => {
    const { error } = await apiService.register(username, email, password);
    if (error) {
      throw new Error(error);
    }
    // Auto-login after successful registration
    await login(username, password);
  };

  /**
   * Logout: clear JWT from localStorage and reset user state.
   * No server call needed — JWT is stateless.
   */
  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  // Provide auth state and actions to all children
  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        signup,
        logout,
        isAuthenticated: !!user,  // True if user object exists
        loading,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


/**
 * Custom hook to access auth context from any component.
 * Usage: const { user, login, logout } = useAuth();
 * Throws if used outside of AuthProvider.
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
