/**
 * BetCard.tsx — Displays a single bet in the public feed.
 *
 * Shows: title, creator avatar, status badge, total stake, challengers,
 * success criteria, and action buttons (Challenge / Dismiss).
 *
 * Key behavior:
 *   - Hides Challenge button on your own bets (shows "Your bet" instead)
 *   - Only shows Challenge on active bets (not resolved/cancelled)
 *   - Clicking a username avatar navigates to their profile page
 *   - Total stake = creator's amount + all active (accepted+pending) challenges
 */
import { useNavigate } from 'react-router-dom'
import { Bet } from '../types'
import { getAvatarUrl } from '../utils/avatar'
import { useAuth } from '../contexts/AuthContext'

interface BetCardProps {
  bet: Bet
  onChallenge: () => void    // Called when "Challenge" button is clicked
  onDismiss: () => void      // Called when "Dismiss" or ✕ button is clicked
  onStar: () => void         // Called when "Star" button is clicked
}

export default function BetCard({ bet, onChallenge, onDismiss, onStar }: BetCardProps) {
  const navigate = useNavigate()
  const { user } = useAuth()

  // Check if this bet belongs to the current user (hide challenge button if so)
  const isOwnBet = user?.username === bet.username

  /** Format a date string into a readable short format (e.g., "Jan 5, 02:30 PM") */
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  /** Map bet status to Tailwind color classes for the status badge */
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'won': return 'bg-friendly-light text-friendly-dark'   // Green
      case 'lost': return 'bg-red-100 text-red-700'                // Red
      case 'cancelled': return 'bg-gray-100 text-gray-700'              // Gray
      default: return 'bg-yellow-100 text-yellow-700'          // Yellow (active)
    }
  }

  // Filter challenges by status for display
  const acceptedChallenges = bet.challenges?.filter(c => c.status === 'accepted') || []
  const allActiveChallenges = bet.challenges?.filter(c => c.status === 'accepted' || c.status === 'pending') || []

  // Calculate total points at stake (creator + all active challengers)
  const challengerStakes = allActiveChallenges.reduce((sum, c) => sum + c.amount, 0)
  const totalStake = bet.amount + challengerStakes

  return (
    <div className="bg-white rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300 overflow-hidden border-2 border-gray-100">
      <div className="p-6">
        {/* ── Header: Title + Creator info + Status badge ── */}
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1 pr-2">
            <h2 className="text-xl font-bold text-gray-800 mb-2">
              {bet.title}
            </h2>
            {/* Creator's avatar + username (clickable → navigates to profile) */}
            {bet.username && (
              <div className="flex items-center gap-2 mb-2">
                <button
                  onClick={() => navigate(`/profile/${bet.username}`)}
                  className="hover:opacity-80 transition-opacity"
                  title={`View ${bet.username}'s profile`}
                >
                  <img
                    src={getAvatarUrl(bet.username || '')}
                    alt={`${bet.username}'s avatar`}
                    className="w-8 h-8 rounded-full border-2 border-competitive-light"
                  />
                </button>
                <span className="text-sm text-gray-500">
                  by <span className="font-semibold text-competitive-dark">@{bet.username}</span>
                </span>
              </div>
            )}
            {/* Color-coded status badge */}
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(bet.status)}`}>
              {bet.status.toUpperCase()}
            </span>
          </div>
          {/* Dismiss button (top-right ✕) */}
          <button
            onClick={onDismiss}
            className="text-gray-400 hover:text-gray-600 transition-colors text-xl font-bold"
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>

        <div className="space-y-3 mb-4">
          {/* ── Total stake display ── */}
          <div className="flex items-center justify-between bg-competitive-light/20 rounded-lg p-3">
            <span className="text-sm font-semibold text-gray-600">Total at Stake:</span>
            <span className="text-xl font-bold text-competitive-dark">{totalStake} points</span>
          </div>

          {/* ── Accepted challengers list (with avatars and amounts) ── */}
          {acceptedChallenges.length > 0 && (
            <div className="bg-gray-50 rounded-lg p-3">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Challengers ({acceptedChallenges.length}):
              </span>
              <div className="mt-2 space-y-2">
                {acceptedChallenges.map(challenge => (
                  <div key={challenge.id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <img
                        src={getAvatarUrl(challenge.challenger_username)}
                        alt={challenge.challenger_username}
                        className="w-5 h-5 rounded-full"
                      />
                      <span className="text-gray-700">@{challenge.challenger_username}</span>
                    </div>
                    <span className="font-semibold text-competitive-dark">{challenge.amount} pts</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Success criteria ── */}
          <div className="bg-gray-50 rounded-lg p-3">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Success Criteria:</span>
            <p className="text-sm text-gray-700 mt-1">{bet.criteria}</p>
          </div>

          {/* ── Creation timestamp ── */}
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span>{formatDate(bet.created_at)}</span>
            {/* ── Star button ── */}
            <button
              onClick={onStar}
              className="flex items-center gap-1 px-3 py-1.5 rounded-full bg-yellow-50 hover:bg-yellow-100 text-yellow-600 hover:text-yellow-700 transition-all active:scale-125 group"
              title="Star this bet"
            >
              <svg
                className="w-4 h-4 transition-transform group-hover:scale-110"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              </svg>
              <span className="text-sm font-semibold">{bet.stars || 0}</span>
            </button>
          </div>
        </div>

        {/* ── Action buttons ── */}
        <div className="flex gap-3">
          {!isOwnBet && (
            <>
              <button
                onClick={onDismiss}
                className="flex-1 px-4 py-2 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
              >
                Dismiss
              </button>
              {/* Only show Challenge button on active bets */}
              {bet.status === 'active' && (
                <button
                  onClick={onChallenge}
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-lg font-semibold hover:from-competitive-DEFAULT hover:to-competitive-light transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
                >
                  Challenge
                </button>
              )}
            </>
          )}
          {/* Show "Your bet" label instead of action buttons on user's own bets */}
          {isOwnBet && (
            <span className="text-sm text-gray-400 italic">Your bet</span>
          )}
        </div>
      </div>
    </div>
  )
}
