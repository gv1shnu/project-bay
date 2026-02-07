import { useState, useEffect, useMemo } from 'react'
import BetCard from '../components/BetCard'
import ChallengeOverlay from '../components/ChallengeOverlay'
import AuthPrompt from '../components/AuthPrompt'
import CreateBetModal from '../components/CreateBetModal'
import { Bet } from '../types'
import { useAuth } from '../contexts/AuthContext'
import { apiService } from '../services/api'
import { getAvatarUrl } from '../utils/avatar'

export default function HomePage() {
  const [bets, setBets] = useState<Bet[]>([])
  const [selectedBet, setSelectedBet] = useState<number | null>(null)
  const [showAuthPrompt, setShowAuthPrompt] = useState(false)
  const [showCreateBet, setShowCreateBet] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [userCount, setUserCount] = useState(0)
  const { user, logout, isAuthenticated, refreshUser } = useAuth()
  const [createBetError, setCreateBetError] = useState<string | null>(null)

  useEffect(() => {
    fetchBets()
  }, [])

  const fetchBets = async () => {
    setLoading(true)
    setError(null)
    const response = await apiService.getPublicBets()
    if (response.data) {
      setBets(response.data)
    } else {
      setError(response.error || 'Failed to fetch bets')
    }
    setLoading(false)

    // Fetch user count
    const countResponse = await apiService.getUserCount()
    if (countResponse.data) {
      setUserCount(countResponse.data.count)
    }
  }

  const filteredBets = useMemo(() => {
    let result = bets.filter(bet => bet.status === 'active')
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(bet =>
        bet.title.toLowerCase().includes(query) ||
        bet.criteria.toLowerCase().includes(query) ||
        bet.username?.toLowerCase().includes(query)
      )
    }
    return result
  }, [bets, searchQuery])

  const handleDismiss = (betId: number) => {
    setBets(bets.filter(bet => bet.id !== betId))
  }

  const handleChallengeClick = (betId: number) => {
    if (!isAuthenticated) {
      setShowAuthPrompt(true)
    } else {
      setSelectedBet(betId)
    }
  }

  const handleCloseOverlay = () => {
    setSelectedBet(null)
  }

  const handleSubmitChallenge = async (betId: number, amount: number) => {
    const response = await apiService.challengeBet(betId, amount)
    if (response.data) {
      await refreshUser()
      await fetchBets()
      setSelectedBet(null)
    } else {
      alert(response.error || 'Failed to create challenge')
    }
  }

  const handleCreateBet = async (title: string, criteria: string, amount: number, deadline: string) => {
    const response = await apiService.createBet(title, criteria, amount, deadline)
    if (response.data) {
      setCreateBetError(null)
      await refreshUser()
      await fetchBets()
      setShowCreateBet(false)
    } else {
      setCreateBetError(
        response.error ||
        "Bets must be written as a personal commitment (e.g. 'I will...')"
      )
    }
  }

  const handleCreateBetClick = () => {
    if (!isAuthenticated) {
      setShowAuthPrompt(true)
    } else {
      setShowCreateBet(true)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-competitive-light/20 via-white to-friendly-light/20">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8">
          <div className="flex justify-between items-center mb-6">
            <div className="text-center flex-1">
              <h1 className="text-5xl font-bold mb-2 bg-gradient-to-r from-competitive-dark to-friendly-dark bg-clip-text text-transparent">
                Bay
              </h1>
              <p className="text-lg text-gray-600">
                Challenge commitments. Win points. Prove yourself.
              </p>
            </div>
            <div className="flex items-center gap-4">
              {user ? (
                <>
                  <a href={`/profile/${user.username}`} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
                    <img
                      src={getAvatarUrl(user.username)}
                      alt={user.username}
                      className="w-10 h-10 rounded-full border-2 border-competitive-light"
                    />
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Signed in as</p>
                      <p className="font-semibold text-gray-800">{user.username}</p>
                      <p className="text-xs text-competitive-dark font-semibold">{user.points} points</p>
                    </div>
                  </a>
                  <button
                    onClick={logout}
                    className="px-4 py-2 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm text-gray-500">Browse bets freely</p>
                    <p className="text-xs text-gray-400">Sign in to challenge</p>
                  </div>
                  <a
                    href="/login"
                    className="px-4 py-2 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-lg font-semibold hover:from-competitive-DEFAULT hover:to-competitive-light transition-all shadow-md"
                  >
                    Sign In
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Search Bar */}
          <div className="max-w-2xl mx-auto">
            <div className="relative">
              <input
                type="text"
                placeholder="Search bets by title, criteria, or username..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-5 py-3 pl-12 rounded-full border-2 border-gray-200 focus:border-competitive-DEFAULT focus:outline-none focus:ring-2 focus:ring-competitive-light/50 transition-all text-gray-700 placeholder-gray-400 shadow-sm hover:shadow-md"
              />
              <svg
                className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              )}
            </div>
            {searchQuery && (
              <p className="text-sm text-gray-500 mt-2 text-center">
                Found {filteredBets.length} bet{filteredBets.length !== 1 ? 's' : ''} matching "{searchQuery}"
              </p>
            )}
          </div>
        </header>

        {loading ? (
          <div className="text-center py-20">
            <p className="text-gray-500 text-lg">Loading bets...</p>
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <p className="text-red-500 text-lg mb-4">{error}</p>
            <button
              onClick={fetchBets}
              className="px-4 py-2 bg-competitive-DEFAULT text-white rounded-lg font-semibold hover:bg-competitive-light transition-colors"
            >
              Retry
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredBets.map((bet) => (
                <BetCard
                  key={bet.id}
                  bet={bet}
                  onChallenge={() => handleChallengeClick(bet.id)}
                  onDismiss={() => handleDismiss(bet.id)}
                />
              ))}
            </div>

            {filteredBets.length === 0 && (
              <div className="text-center py-20">
                <p className="text-gray-500 text-lg">
                  {searchQuery ? 'No bets match your search.' : 'No bets available. Create one to get started!'}
                </p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Floating Action Button - Create Bet */}
      <button
        onClick={handleCreateBetClick}
        className="fixed bottom-8 right-8 w-16 h-16 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-full shadow-lg hover:shadow-xl transition-all hover:scale-110 flex items-center justify-center text-3xl font-bold"
        title="Create a new bet"
      >
        +
      </button>

      {showAuthPrompt && (
        <AuthPrompt onClose={() => setShowAuthPrompt(false)} />
      )}
      {selectedBet && (
        <ChallengeOverlay
          betId={selectedBet}
          onClose={handleCloseOverlay}
          onSubmit={handleSubmitChallenge}
        />
      )}
      {showCreateBet && (
        <CreateBetModal
          onClose={() => {
            setShowCreateBet(false)
            setCreateBetError(null)
          }}
          onSubmit={handleCreateBet}
          error={createBetError}
          onClearError={() => setCreateBetError(null)}
        />
      )}

      {/* Footer with user count */}
      {userCount > 0 && (
        <footer className="mt-16 pb-24 text-center">
          <p className="text-gray-400 text-sm">
            <span className="font-semibold text-gray-500">{userCount}</span> users registered so far
          </p>
        </footer>
      )}
    </div>
  )
}
