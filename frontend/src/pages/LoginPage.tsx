/**
 * LoginPage.tsx — User sign-in page.
 *
 * Simple form with username + password fields.
 * On success, navigates to the homepage ("/").
 * Uses AuthContext.login() which stores the JWT and hydrates user state.
 */
import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  // Form state
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')       // Error message to display
  const [loading, setLoading] = useState(false) // Prevents double-submission

  const { login } = useAuth()
  const navigate = useNavigate()

  /** Handle form submission — authenticate and redirect on success */
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      navigate('/')  // Redirect to homepage after successful login
    } catch (err) {
      setError('An error occurred. Please try again.')
    } finally {
      setLoading(false)  // Re-enable the submit button
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-competitive-light/20 via-white to-friendly-light/20 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        {/* App branding */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-competitive-dark to-friendly-dark bg-clip-text text-transparent">
            Bay
          </h1>
          <p className="text-xl text-gray-600">Welcome back!</p>
        </div>

        {/* Login card */}
        <div className="bg-white rounded-2xl shadow-xl p-8 border-2 border-gray-100">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Sign In</h2>

          {/* Error banner */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username field */}
            <div>
              <label htmlFor="username" className="block text-sm font-semibold text-gray-700 mb-2">
                Username
              </label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-competitive-DEFAULT focus:ring-2 focus:ring-competitive-light"
                placeholder="Enter your username"
              />
            </div>

            {/* Password field */}
            <div>
              <label htmlFor="password" className="block text-sm font-semibold text-gray-700 mb-2">
                Password
              </label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-competitive-DEFAULT focus:ring-2 focus:ring-competitive-light"
                placeholder="Enter your password"
              />
            </div>

            {/* Submit button — disabled while loading to prevent double-submission */}
            <button
              type="submit"
              disabled={loading}
              className="w-full px-6 py-3 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-lg font-semibold hover:from-competitive-DEFAULT hover:to-competitive-light transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {/* Link to signup page */}
          <div className="mt-6 text-center">
            <p className="text-gray-600">
              Don't have an account?{' '}
              <Link
                to="/signup"
                className="text-competitive-dark hover:text-competitive-DEFAULT font-semibold transition-colors"
              >
                Sign up
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
