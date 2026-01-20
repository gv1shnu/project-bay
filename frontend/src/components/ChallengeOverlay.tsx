import { useState, FormEvent, useEffect, MouseEvent } from 'react'
import { useAuth } from '../contexts/AuthContext'

interface ChallengeOverlayProps {
  betId: number
  onClose: () => void
  onSubmit: (betId: number, amount: number) => void
}

export default function ChallengeOverlay({ betId, onClose, onSubmit }: ChallengeOverlayProps) {
  const { isAuthenticated } = useAuth()
  const [amount, setAmount] = useState<string>('')
  const [error, setError] = useState<string>('')

  useEffect(() => {
    // Prevent body scroll when overlay is open
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setError('')

    const numAmount = parseFloat(amount)
    
    if (!amount || isNaN(numAmount) || numAmount <= 0) {
      setError('Please enter a valid bet amount greater than 0')
      return
    }

    if (numAmount < 1) {
      setError('Minimum bet amount is 1 point')
      return
    }

    onSubmit(betId, numAmount)
  }

  const handleBackdropClick = (e: MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  if (!isAuthenticated) {
    return null // AuthPrompt will be shown instead
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 transform transition-all">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-3xl font-bold bg-gradient-to-r from-competitive-dark to-friendly-dark bg-clip-text text-transparent">
            Challenge This Bet
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
          Enter the amount of points you want to bet. If the challenger fails to meet their commitment, you win these points!
        </p>

        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label htmlFor="amount" className="block text-sm font-semibold text-gray-700 mb-2">
              Bet Amount (Points)
            </label>
            <div className="relative">
              <input
                type="number"
                id="amount"
                value={amount}
                onChange={(e) => {
                  setAmount(e.target.value)
                  setError('')
                }}
                min="1"
                step="1"
                placeholder="Enter amount"
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-competitive-DEFAULT focus:ring-2 focus:ring-competitive-light text-lg"
                autoFocus
              />
            </div>
            {error && (
              <p className="mt-2 text-sm text-red-600">{error}</p>
            )}
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-6 py-3 bg-gradient-to-r from-friendly-dark to-friendly-DEFAULT text-white rounded-lg font-semibold hover:from-friendly-DEFAULT hover:to-friendly-light transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
            >
              Submit Challenge
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

