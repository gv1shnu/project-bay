import { useNavigate } from 'react-router-dom'
import { Bet } from '../types'
import { getAvatarUrl } from '../utils/avatar'
import { useAuth } from '../contexts/AuthContext'

interface BetCardProps {
  bet: Bet
  onChallenge: () => void
  onDismiss: () => void
}

export default function BetCard({ bet, onChallenge, onDismiss }: BetCardProps) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const isOwnBet = user?.username === bet.username
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'won':
        return 'bg-friendly-light text-friendly-dark'
      case 'lost':
        return 'bg-red-100 text-red-700'
      case 'cancelled':
        return 'bg-gray-100 text-gray-700'
      default:
        return 'bg-yellow-100 text-yellow-700'
    }
  }

  const acceptedChallenges = bet.challenges?.filter(c => c.status === 'accepted') || []
  const allActiveChallenges = bet.challenges?.filter(c => c.status === 'accepted' || c.status === 'pending') || []
  const challengerStakes = allActiveChallenges.reduce((sum, c) => sum + c.amount, 0)
  const totalStake = bet.amount + challengerStakes  // Creator's stake + all active challengers

  return (
    <div className="bg-white rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300 overflow-hidden border-2 border-gray-100">
      <div className="p-6">
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1 pr-2">
            <h2 className="text-xl font-bold text-gray-800 mb-2">
              {bet.title}
            </h2>
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
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(bet.status)}`}>
              {bet.status.toUpperCase()}
            </span>
          </div>
          <button
            onClick={onDismiss}
            className="text-gray-400 hover:text-gray-600 transition-colors text-xl font-bold"
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>

        <div className="space-y-3 mb-4">
          {/* Stakes info */}
          <div className="flex items-center justify-between bg-competitive-light/20 rounded-lg p-3">
            <span className="text-sm font-semibold text-gray-600">Total at Stake:</span>
            <span className="text-xl font-bold text-competitive-dark">{totalStake} points</span>
          </div>

          {/* Challengers */}
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

          {/* Criteria */}
          <div className="bg-gray-50 rounded-lg p-3">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Success Criteria:</span>
            <p className="text-sm text-gray-700 mt-1">{bet.criteria}</p>
          </div>

          <div className="flex items-center text-xs text-gray-400">
            <span>{formatDate(bet.created_at)}</span>
          </div>
        </div>

        <div className="flex gap-3">
          {!isOwnBet && (
            <>
              <button
                onClick={onDismiss}
                className="flex-1 px-4 py-2 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
              >
                Dismiss
              </button>
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
          {isOwnBet && (
            <span className="text-sm text-gray-400 italic">Your bet</span>
          )}
        </div>
      </div>
    </div>
  )
}
