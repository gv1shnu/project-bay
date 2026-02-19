/**
 * BetCard.tsx — Compact bet card for the public feed.
 *
 * Shows only: title, creator avatar + username, total stake, star count, status badge.
 * Clicking the card opens the BetDetailModal for full details.
 */
import { useNavigate } from 'react-router-dom'
import { Bet } from '../types'
import { getAvatarUrl } from '../utils/avatar'
import { useAuth } from '../contexts/AuthContext'

interface BetCardProps {
  bet: Bet
  onCardClick: () => void   // Opens the detail modal
  onStar: () => void        // Toggle star
}

export default function BetCard({ bet, onCardClick, onStar }: BetCardProps) {
  const navigate = useNavigate()
  const { user } = useAuth()

  // Check if current user starred this bet
  const isStarred = user && bet.starred_by_user_ids?.includes(user.id)

  // Calculate total points at stake (creator + all active challengers)
  const allActiveChallenges = bet.challenges?.filter(c => c.status === 'accepted' || c.status === 'pending') || []
  const challengerStakes = allActiveChallenges.reduce((sum, c) => sum + c.amount, 0)
  const totalStake = bet.amount + challengerStakes

  /** Map bet status to Tailwind color classes */
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'won': return 'bg-friendly-light text-friendly-dark'
      case 'lost': return 'bg-red-100 text-red-700'
      case 'cancelled': return 'bg-gray-100 text-gray-700'
      case 'proof_under_review': return 'bg-blue-100 text-blue-700'
      default: return 'bg-yellow-100 text-yellow-700'
    }
  }

  /** Map status to human-friendly labels */
  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'proof_under_review': return 'UNDER REVIEW'
      default: return status.toUpperCase()
    }
  }

  return (
    <div
      className="bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden border-2 border-gray-100 cursor-pointer hover:-translate-y-0.5"
      onClick={onCardClick}
    >
      <div className="p-5">
        {/* Top row: status badge */}
        <div className="flex items-center justify-between mb-3">
          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${getStatusColor(bet.status)}`}>
            {getStatusLabel(bet.status)}
          </span>
          {/* Star button — stop propagation so it doesn't open modal */}
          <button
            onClick={e => { e.stopPropagation(); onStar() }}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-full transition-all active:scale-125 group ${isStarred
              ? 'bg-yellow-200 text-yellow-700 hover:bg-yellow-300'
              : 'bg-yellow-50 hover:bg-yellow-100 text-yellow-500 hover:text-yellow-600'
              }`}
            title={isStarred ? 'Unstar' : 'Star'}
          >
            <svg className="w-3.5 h-3.5 transition-transform group-hover:scale-110" fill="currentColor" viewBox="0 0 24 24">
              {isStarred ? (
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              ) : (
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" strokeWidth="1.5" stroke="currentColor" fill="none" />
              )}
            </svg>
            <span className="text-xs font-bold">{bet.stars || 0}</span>
          </button>
        </div>

        {/* Title */}
        <h2 className="text-lg font-bold text-gray-800 mb-3 line-clamp-2 leading-snug">{bet.title}</h2>

        {/* Bottom row: avatar + username + stake */}
        <div className="flex items-center justify-between">
          {/* Creator info */}
          {bet.username && (
            <div className="flex items-center gap-2">
              <button
                onClick={e => { e.stopPropagation(); navigate(`/profile/${bet.username}`) }}
                className="hover:opacity-80 transition-opacity"
                title={`View ${bet.username}'s profile`}
              >
                <img
                  src={getAvatarUrl(bet.username || '')}
                  alt={`${bet.username}'s avatar`}
                  className="w-7 h-7 rounded-full border-2 border-competitive-light"
                />
              </button>
              <span className="text-xs text-gray-500 font-medium">@{bet.username}</span>
            </div>
          )}
          {/* Stake */}
          <span className="text-sm font-bold text-competitive-dark bg-competitive-light/20 px-2.5 py-1 rounded-lg">
            {totalStake} pts
          </span>
        </div>
      </div>
    </div>
  )
}
