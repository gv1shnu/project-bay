import { createContext, useContext, useState, ReactNode, useEffect } from 'react'
import { apiService } from '../services/api'

interface User {
  id: number
  email: string
  username: string
  points: number
}

interface AuthContextType {
  user: User | null
  login: (username: string, password: string) => Promise<boolean>
  signup: (email: string, password: string, username: string) => Promise<boolean>
  logout: () => void
  isAuthenticated: boolean
  loading: boolean
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Check for existing token and fetch user on mount
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      refreshUser()
    } else {
      setLoading(false)
    }
  }, [])

  const refreshUser = async () => {
    const response = await apiService.getCurrentUser()
    if (response.data) {
      setUser({
        id: response.data.id,
        email: response.data.email,
        username: response.data.username,
        points: response.data.points,
      })
    } else {
      // Token might be invalid, clear it
      apiService.logout()
      setUser(null)
    }
    setLoading(false)
  }

  const login = async (username: string, password: string): Promise<boolean> => {
    const response = await apiService.login(username, password)
    if (response.data) {
      // Fetch user info after successful login
      await refreshUser()
      return true
    }
    return false
  }

  const signup = async (email: string, password: string, username: string): Promise<boolean> => {
    const response = await apiService.register(username, email, password)
    if (response.data) {
      // Registration triggers login, so fetch user info
      await refreshUser()
      return true
    }
    return false
  }

  const logout = () => {
    apiService.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        signup,
        logout,
        isAuthenticated: !!user,
        loading,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

