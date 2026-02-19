/**
 * BetDetailModal.tsx — Full-detail overlay for a bet.
 *
 * Opened when user clicks a compact BetCard in the feed.
 * Shows: bet info, criteria, deadline, challengers, proof status,
 * and action buttons (Challenge, Dismiss, Upload Proof).
 * Closes on backdrop click or ✕ button.
 */
import { useNavigate } from 'react-router-dom'
import { Bet } from '../types'
import { getAvatarUrl } from '../utils/avatar'
import { useAuth } from '../contexts/AuthContext'

interface BetDetailModalProps {
    bet: Bet
    onClose: () => void
    onChallenge: () => void
    onDismiss: () => void
    onStar: () => void
    onUploadProof?: () => void
}

export default function BetDetailModal({ bet, onClose, onChallenge, onDismiss, onStar, onUploadProof }: BetDetailModalProps) {
    const navigate = useNavigate()
    const { user } = useAuth()

    const isOwnBet = user?.username === bet.username
    const isStarred = user && bet.starred_by_user_ids?.includes(user.id)

    const acceptedChallenges = bet.challenges?.filter(c => c.status === 'accepted') || []
    const allActiveChallenges = bet.challenges?.filter(c => c.status === 'accepted' || c.status === 'pending') || []
    const challengerStakes = allActiveChallenges.reduce((sum, c) => sum + c.amount, 0)
    const totalStake = bet.amount + challengerStakes

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        })
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'won': return 'bg-friendly-light text-friendly-dark'
            case 'lost': return 'bg-red-100 text-red-700'
            case 'cancelled': return 'bg-gray-100 text-gray-700'
            case 'proof_under_review': return 'bg-blue-100 text-blue-700'
            default: return 'bg-yellow-100 text-yellow-700'
        }
    }

    const getStatusLabel = (status: string) => {
        switch (status) {
            case 'proof_under_review': return 'PROOF UNDER REVIEW'
            default: return status.toUpperCase()
        }
    }

    return (
        /* Backdrop — click outside to close */
        <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={onClose}
        >
            {/* Modal card */}
            <div
                className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
                onClick={e => e.stopPropagation()}
            >
                <div className="p-6">
                    {/* Header: close button */}
                    <div className="flex justify-between items-start mb-4">
                        <div className="flex-1">
                            {/* Status badge */}
                            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(bet.status)}`}>
                                {getStatusLabel(bet.status)}
                            </span>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-600 transition-colors text-2xl font-bold leading-none"
                            aria-label="Close"
                        >
                            ×
                        </button>
                    </div>

                    {/* Title */}
                    <h2 className="text-2xl font-bold text-gray-800 mb-3">{bet.title}</h2>

                    {/* Creator info */}
                    {bet.username && (
                        <div className="flex items-center gap-2 mb-4">
                            <button
                                onClick={() => { onClose(); navigate(`/profile/${bet.username}`) }}
                                className="hover:opacity-80 transition-opacity"
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

                    {/* Details grid */}
                    <div className="space-y-3 mb-5">
                        {/* Total stake */}
                        <div className="flex items-center justify-between bg-competitive-light/20 rounded-lg p-3">
                            <span className="text-sm font-semibold text-gray-600">Total at Stake:</span>
                            <span className="text-xl font-bold text-competitive-dark">{totalStake} points</span>
                        </div>

                        {/* Success criteria */}
                        <div className="bg-gray-50 rounded-lg p-3">
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Success Criteria:</span>
                            <p className="text-sm text-gray-700 mt-1">{bet.criteria}</p>
                        </div>

                        {/* Deadline */}
                        <div className="bg-gray-50 rounded-lg p-3">
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Deadline:</span>
                            <p className="text-sm text-gray-700 mt-1">{formatDate(bet.deadline)}</p>
                        </div>

                        {/* Challengers */}
                        {/* Challengers */}
                        {allActiveChallenges.length > 0 && (
                            <div className="bg-gray-50 rounded-lg p-3">
                                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                                    Challengers ({allActiveChallenges.length}):
                                </span>
                                <div className="mt-2 space-y-2">
                                    {allActiveChallenges.map(challenge => (
                                        <div key={challenge.id} className="flex items-center justify-between text-sm">
                                            <div className="flex items-center gap-2">
                                                <img
                                                    src={getAvatarUrl(challenge.challenger_username)}
                                                    alt={challenge.challenger_username}
                                                    className="w-5 h-5 rounded-full"
                                                />
                                                <span className="text-gray-700">@{challenge.challenger_username}</span>
                                                {challenge.status === 'pending' && (
                                                    <span className="text-[10px] bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded-full">Pending</span>
                                                )}
                                            </div>
                                            <span className="font-semibold text-competitive-dark">{challenge.amount} pts</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Proof vote status */}
                        {bet.status === 'proof_under_review' && bet.proof_votes && (
                            <div className="bg-blue-50 rounded-lg p-3">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <span className="text-xs font-semibold text-blue-600 uppercase tracking-wide">Proof Votes:</span>
                                        <p className="text-sm font-semibold text-blue-800 mt-0.5">
                                            {bet.proof_votes.filter(v => v.vote === 'cool').length}/{acceptedChallenges.length} voted COOL
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => { onClose(); navigate(`/bets/${bet.id}/proof`) }}
                                        className="text-xs font-bold text-blue-600 hover:text-blue-800 underline"
                                    >
                                        Review Proof →
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Timestamp + Star */}
                        <div className="flex items-center justify-between text-xs text-gray-400">
                            <span>Created {formatDate(bet.created_at)}</span>
                            <button
                                onClick={onStar}
                                className={`flex items-center gap-1 px-3 py-1.5 rounded-full transition-all active:scale-125 group ${isStarred
                                    ? 'bg-yellow-200 text-yellow-700 hover:bg-yellow-300'
                                    : 'bg-yellow-50 hover:bg-yellow-100 text-yellow-600 hover:text-yellow-700'
                                    }`}
                                title={isStarred ? 'Unstar this bet' : 'Star this bet'}
                            >
                                <svg className="w-4 h-4 transition-transform group-hover:scale-110" fill="currentColor" viewBox="0 0 24 24">
                                    {isStarred ? (
                                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                                    ) : (
                                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" strokeWidth="1.5" stroke="currentColor" fill="none" />
                                    )}
                                </svg>
                                <span className="text-sm font-semibold">{bet.stars || 0}</span>
                            </button>
                        </div>
                    </div>

                    {/* Action buttons */}
                    <div className="flex gap-3 pt-2 border-t border-gray-100">
                        {/* Upload Proof — creator only, active bet, must have challengers */}
                        {isOwnBet && bet.status === 'active' && onUploadProof && allActiveChallenges.length > 0 && (
                            <button
                                onClick={onUploadProof}
                                className="flex-1 px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg font-semibold hover:from-amber-600 hover:to-orange-600 transition-all shadow-md hover:shadow-lg"
                            >
                                📷 Upload Proof
                            </button>
                        )}
                        {/* Proof Submitted badge */}
                        {isOwnBet && bet.status === 'proof_under_review' && (
                            <span className="flex-1 px-4 py-2 bg-blue-50 text-blue-700 rounded-lg font-semibold text-center border-2 border-blue-200">
                                ✅ Proof Submitted
                            </span>
                        )}
                        {/* Challenge + Dismiss — for other users */}
                        {!isOwnBet && (
                            <>
                                <button
                                    onClick={onDismiss}
                                    className="flex-1 px-4 py-2 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
                                >
                                    Dismiss
                                </button>
                                {bet.status === 'active' && (
                                    (() => {
                                        const hasChallenged = user && allActiveChallenges.some(c => c.challenger_id === user.id)
                                        return hasChallenged ? (
                                            <button
                                                disabled
                                                className="flex-1 px-4 py-2 bg-gray-100 text-gray-400 rounded-lg font-semibold cursor-not-allowed border border-gray-200"
                                            >
                                                Already Challenged
                                            </button>
                                        ) : (
                                            <button
                                                onClick={onChallenge}
                                                className="flex-1 px-4 py-2 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-lg font-semibold hover:from-competitive-DEFAULT hover:to-competitive-light transition-all shadow-md hover:shadow-lg"
                                            >
                                                Challenge
                                            </button>
                                        )
                                    })()
                                )}
                            </>
                        )}
                        {/* Your bet label */}
                        {isOwnBet && bet.status !== 'proof_under_review' && (
                            <span className="text-sm text-gray-400 italic">Your bet</span>
                        )}
                    </div>
                </div>
            </div >
        </div >
    )
}
