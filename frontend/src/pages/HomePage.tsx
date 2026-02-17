/**
 * HomePage.tsx — Main feed page showing all public bets.
 *
 * This is the primary page users see. Features:
 *   - Search bar for filtering bets by title, criteria, or username (client-side)
 *   - 3-column responsive grid of BetCard components
 *   - "Create Bet" floating action button (FAB)
 *   - Challenge flow: click Challenge → ChallengeOverlay → submit
 *   - Auth prompts for unauthenticated users trying restricted actions
 *   - Footer showing total registered user count
 *
 * Data flow:
 *   fetchBets() → apiService.getPublicBets() → setBets() → filteredBets (useMemo) → BetCard grid
 */
import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import BetCard from '../components/BetCard'
import ChallengeOverlay from '../components/ChallengeOverlay'
import AuthPrompt from '../components/AuthPrompt'
import CreateBetModal from '../components/CreateBetModal'
import ProofUploadModal from '../components/ProofUploadModal'
import { Bet } from '../types'
import { useAuth } from '../contexts/AuthContext'
import { apiService } from '../services/api'
import { getAvatarUrl } from '../utils/avatar'

export default function HomePage() {
  const navigate = useNavigate()
  // ── State ──
  const [bets, setBets] = useState<Bet[]>([])                    // All public bets from API
  const [selectedBet, setSelectedBet] = useState<number | null>(null)  // Bet ID being challenged (null = no overlay)
  const [showAuthPrompt, setShowAuthPrompt] = useState(false)    // Show login prompt modal
  const [showCreateBet, setShowCreateBet] = useState(false)      // Show create bet modal
  const [loading, setLoading] = useState(true)                   // Initial data loading state
  const [error, setError] = useState<string | null>(null)        // API error message
  const [searchQuery, setSearchQuery] = useState('')             // Search input value
  const [userCount, setUserCount] = useState(0)                  // Total registered users (footer)
  const { user, logout, isAuthenticated, refreshUser } = useAuth()
  const [createBetError, setCreateBetError] = useState<string | null>(null)  // Error from create bet API
  const [proofBetId, setProofBetId] = useState<number | null>(null) // Bet ID for proof upload modal

  // Fetch bets on mount + auto-refresh every 30 seconds
  useEffect(() => {
    fetchBets()
    const interval = setInterval(fetchBets, 30000)
    return () => clearInterval(interval)
  }, [])

  /** Fetch all public bets and user count from the API */
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

    // Also fetch total user count for the footer
    const countResponse = await apiService.getUserCount()
    if (countResponse.data) {
      setUserCount(countResponse.data.count)
    }
  }

  /**
   * Client-side search filter using useMemo for performance.
   * Only shows active bets. Filters by title, criteria, or username.
   * Re-computes only when bets or searchQuery changes.
   */
  const filteredBets = useMemo(() => {
    let result = bets.filter(bet =>
      bet.status === 'active' || bet.status === 'awaiting_proof' || bet.status === 'proof_under_review'
    )
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

  /** Remove a bet from the local feed (client-side only — doesn't delete from server) */
  const handleDismiss = (betId: number) => {
    setBets(bets.filter(bet => bet.id !== betId))
  }

  /** Handle Challenge button click — show auth prompt if not logged in, otherwise open overlay */
  const handleChallengeClick = (betId: number) => {
    if (!isAuthenticated) {
      setShowAuthPrompt(true)
    } else {
      setSelectedBet(betId)
    }
  }

  /** Close the challenge overlay */
  const handleCloseOverlay = () => {
    setSelectedBet(null)
  }

  /** Submit a challenge: call API, refresh user points and bet feed on success */
  const handleSubmitChallenge = async (betId: number, amount: number) => {
    const response = await apiService.challengeBet(betId, amount)
    if (response.data) {
      await refreshUser()  // Update points display
      await fetchBets()    // Refresh feed to show the new challenge
      setSelectedBet(null) // Close overlay
    } else {
      alert(response.error || 'Failed to create challenge')
    }
  }

  /** Submit a new bet: call API, refresh everything on success */
  const handleCreateBet = async (title: string, criteria: string, amount: number, deadline: string) => {
    const response = await apiService.createBet(title, criteria, amount, deadline)
    if (response.data) {
      setCreateBetError(null)
      await refreshUser()     // Update points display
      await fetchBets()       // Refresh feed to show the new bet
      setShowCreateBet(false) // Close modal
    } else {
      // Show error to user (e.g., "Bets must be written as a personal commitment")
      setCreateBetError(
        response.error ||
        "Bets must be written as a personal commitment (e.g. 'I will...')"
      )
    }
  }

  /** Handle star button — increment star count and refresh (optimistic update) */
  const handleStar = async (betId: number) => {
    // Optimistic update: increment locally first for instant feedback
    setBets(prev => prev.map(b => b.id === betId ? { ...b, stars: (b.stars || 0) + 1 } : b))
    const response = await apiService.starBet(betId)
    if (!response.data) {
      // Revert on failure
      setBets(prev => prev.map(b => b.id === betId ? { ...b, stars: (b.stars || 0) - 1 } : b))
    }
  }

  /** Handle Create Bet button — show auth prompt if not logged in */
  const handleCreateBetClick = () => {
    if (!isAuthenticated) {
      setShowAuthPrompt(true)
    } else {
      setShowCreateBet(true)
    }
  }

  /** Handle proof upload for a bet */
  const handleProofSubmit = async (comment: string, file: File) => {
    if (!proofBetId) return
    const response = await apiService.submitProof(proofBetId, comment, file)
    if (response.data) {
      setProofBetId(null)
      await fetchBets()   // Refresh to show updated status
    } else {
      throw new Error(response.error || 'Failed to upload proof')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-competitive-light/20 via-white to-friendly-light/20">
      <div className="container mx-auto px-4 py-8">
        {/* ══════════════ Header Section ══════════════ */}
        <header className="mb-8">
          <div className="flex justify-between items-center mb-6">
            {/* App title and tagline */}
            <div className="text-center flex-1">
              <h1 className="text-5xl font-bold mb-2 bg-gradient-to-r from-competitive-dark to-friendly-dark bg-clip-text text-transparent">
                Bay
              </h1>
              <p className="text-lg text-gray-600">
                Challenge commitments. Win points. Prove yourself.
              </p>
            </div>
            {/* User info or sign-in button (top-right) */}
            <div className="flex items-center gap-4">
              {user ? (
                <>
                  {/* Logged in: show avatar, username, points, notification bell, and logout */}
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
                  {/* Notification bell */}
                  <button
                    onClick={() => navigate('/notifications')}
                    className="relative p-2 text-gray-400 hover:text-competitive-dark transition-colors hover:bg-gray-100 rounded-full"
                    title="Notifications"
                    aria-label="Notifications"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                    </svg>
                  </button>
                  <button
                    onClick={logout}
                    className="px-4 py-2 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
                  >
                    Logout
                  </button>
                </>
              ) : (
                /* Not logged in: show sign-in prompt */
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
                  <a
                    href="/signup"
                    className="px-4 py-2 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
                  >
                    Sign Up
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* ── Search Bar ── */}
          <div className="max-w-2xl mx-auto">
            <div className="relative">
              <input
                type="text"
                placeholder="Search bets by title, criteria, or username..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-5 py-3 pl-12 rounded-full border-2 border-gray-200 focus:border-competitive-DEFAULT focus:outline-none focus:ring-2 focus:ring-competitive-light/50 transition-all text-gray-700 placeholder-gray-400 shadow-sm hover:shadow-md"
              />
              {/* Search icon */}
              <svg
                className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              {/* Clear search button (only visible when search has text) */}
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              )}
            </div>
            {/* Search results count */}
            {searchQuery && (
              <p className="text-sm text-gray-500 mt-2 text-center">
                Found {filteredBets.length} bet{filteredBets.length !== 1 ? 's' : ''} matching "{searchQuery}"
              </p>
            )}
          </div>
        </header>

        {/* ══════════════ Main Content: Bet Feed ══════════════ */}
        {loading ? (
          <div className="text-center py-20">
            <p className="text-gray-500 text-lg">Loading bets...</p>
          </div>
        ) : error ? (
          /* Error state with retry button */
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
            {/* Responsive grid: 1 col mobile, 2 cols tablet, 3 cols desktop */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredBets.map((bet) => (
                <BetCard
                  key={bet.id}
                  bet={bet}
                  onChallenge={() => handleChallengeClick(bet.id)}
                  onDismiss={() => handleDismiss(bet.id)}
                  onStar={() => handleStar(bet.id)}
                  onUploadProof={bet.status === 'awaiting_proof' ? () => setProofBetId(bet.id) : undefined}
                />
              ))}
            </div>

            {/* Empty state */}
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

      {/* ══════════════ Floating Action Button (FAB) ══════════════ */}
      <button
        onClick={handleCreateBetClick}
        className="fixed bottom-8 right-8 w-16 h-16 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-full shadow-lg hover:shadow-xl transition-all hover:scale-110 flex items-center justify-center text-3xl font-bold"
        title="Create a new bet"
      >
        +
      </button>

      {/* ══════════════ Modals / Overlays ══════════════ */}
      {/* Auth prompt — shown when unauthenticated user tries to challenge/create */}
      {showAuthPrompt && (
        <AuthPrompt onClose={() => setShowAuthPrompt(false)} />
      )}
      {/* Challenge overlay — shown when challenging a specific bet */}
      {selectedBet && (
        <ChallengeOverlay
          betId={selectedBet}
          onClose={handleCloseOverlay}
          onSubmit={handleSubmitChallenge}
        />
      )}
      {/* Create bet modal — shown when creating a new bet */}
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
      {/* Proof upload modal — shown when creator clicks Upload Proof */}
      {proofBetId && (() => {
        const proofBet = bets.find(b => b.id === proofBetId)
        return proofBet ? (
          <ProofUploadModal
            betTitle={proofBet.title}
            proofDeadline={proofBet.proof_deadline || proofBet.deadline}
            onClose={() => setProofBetId(null)}
            onSubmit={handleProofSubmit}
          />
        ) : null
      })()}

      {/* ══════════════ Footer ══════════════ */}
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
