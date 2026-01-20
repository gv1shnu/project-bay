import { Link, useNavigate } from 'react-router-dom'
import { MouseEvent } from 'react'

interface AuthPromptProps {
  onClose: () => void
}

export default function AuthPrompt({ onClose }: AuthPromptProps) {
  const navigate = useNavigate()

  const handleBackdropClick = (e: MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  const handleLoginClick = () => {
    navigate('/login')
    onClose()
  }

  const handleSignupClick = () => {
    navigate('/signup')
    onClose()
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 transform transition-all">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-3xl font-bold bg-gradient-to-r from-competitive-dark to-friendly-dark bg-clip-text text-transparent">
            Sign In Required
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors text-3xl font-light leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <p className="text-gray-600 mb-6">
          You need to be signed in to challenge a bet. Sign in to your account or create a new one to get started!
        </p>

        <div className="space-y-3">
          <button
            onClick={handleLoginClick}
            className="w-full px-6 py-3 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-lg font-semibold hover:from-competitive-DEFAULT hover:to-competitive-light transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
          >
            Sign In
          </button>
          <button
            onClick={handleSignupClick}
            className="w-full px-6 py-3 bg-gradient-to-r from-friendly-dark to-friendly-DEFAULT text-white rounded-lg font-semibold hover:from-friendly-DEFAULT hover:to-friendly-light transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
          >
            Create Account
          </button>
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-sm transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

