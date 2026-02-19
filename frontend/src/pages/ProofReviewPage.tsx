/**
 * ProofReviewPage.tsx — View uploaded proof and vote COOL / NOT COOL.
 *
 * Accessed via /bets/:betId/proof (linked from notifications).
 * Shows proof media, creator's comment, vote buttons with confirmation,
 * and the list of votes cast so far. Auto-resolves the bet when majority is reached.
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { apiService } from '../services/api'
import { Bet } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function ProofReviewPage() {
    const { betId } = useParams<{ betId: string }>()
    const navigate = useNavigate()
    const { user, isAuthenticated, loading: authLoading } = useAuth()

    const [bet, setBet] = useState<Bet | null>(null)
    const [loading, setLoading] = useState(true)
    const [voting, setVoting] = useState(false)
    const [confirmVote, setConfirmVote] = useState<'cool' | 'not_cool' | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [voteResult, setVoteResult] = useState<{ bet_status: string; cool_count: number; total_voters: number } | null>(null)

    useEffect(() => {
        // Wait for auth to finish loading before checking
        if (authLoading) return
        if (!isAuthenticated) {
            navigate('/login')
            return
        }
        fetchBet()
    }, [betId, isAuthenticated, authLoading])

    const fetchBet = async () => {
        if (!betId) return
        setLoading(true)
        // Use the public feed to get full bet data with votes
        const response = await apiService.getPublicBets()
        if (response.data) {
            const found = response.data.find((b: Bet) => b.id === Number(betId))
            if (found) setBet(found)
            else setError('Bet not found')
        } else {
            setError('Failed to load bet')
        }
        setLoading(false)
    }

    const handleVote = async (vote: 'cool' | 'not_cool') => {
        if (!betId) return
        setVoting(true)
        setError(null)
        const response = await apiService.voteOnProof(Number(betId), vote)
        if (response.data) {
            setVoteResult(response.data)
            setConfirmVote(null)
            // Refresh bet data to reflect updated votes
            await fetchBet()
        } else {
            setError(response.error || 'Failed to submit vote')
        }
        setVoting(false)
    }

    const hasVoted = bet?.proof_votes?.some(v => v.user_id === user?.id)
    const myVote = bet?.proof_votes?.find(v => v.user_id === user?.id)
    const isChallenger = bet?.challenges?.some(
        c => c.challenger_id === user?.id && (c.status === 'accepted' || c.status === 'pending')
    )
    const totalVotes = bet?.proof_votes?.length ?? 0
    const totalVoters = bet?.challenges?.filter(c => c.status === 'accepted' || c.status === 'pending').length ?? 0

    /** Determine media type from URL */
    const isVideo = (url: string) => /\.(mp4|mov|webm)$/i.test(url)

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-competitive-light/20 via-white to-friendly-light/20 flex items-center justify-center">
                <p className="text-gray-500 text-lg">Loading proof...</p>
            </div>
        )
    }

    if (!bet || error) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-competitive-light/20 via-white to-friendly-light/20 flex items-center justify-center">
                <div className="text-center">
                    <p className="text-red-500 text-lg mb-4">{error || 'Bet not found'}</p>
                    <button onClick={() => navigate('/')} className="text-competitive-dark hover:underline">Back to home</button>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-competitive-light/20 via-white to-friendly-light/20">
            <div className="container mx-auto px-4 py-8 max-w-2xl">
                {/* Header */}
                <div className="flex items-center gap-4 mb-8">
                    <button
                        onClick={() => navigate('/notifications')}
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                        aria-label="Back to notifications"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                    </button>
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-competitive-dark to-friendly-dark bg-clip-text text-transparent">
                        Proof Review
                    </h1>
                </div>

                {/* Bet info */}
                <div className="bg-white rounded-2xl shadow-lg border-2 border-gray-100 p-6 mb-6">
                    <div className="flex items-center gap-2 mb-3">
                        <span className="text-xs font-bold px-2 py-1 rounded-full bg-yellow-100 text-yellow-800">
                            {bet.status === 'proof_under_review' ? '🔍 Under Review' :
                                bet.status === 'won' ? '✅ Won' :
                                    bet.status === 'lost' ? '❌ Lost' : bet.status}
                        </span>
                        <span className="text-xs text-gray-400">by @{bet.username}</span>
                    </div>
                    <h2 className="text-xl font-bold text-gray-800 mb-1">{bet.title}</h2>
                    <p className="text-sm text-gray-500 mb-1">
                        <strong>Criteria:</strong> {bet.criteria}
                    </p>
                    <p className="text-sm text-gray-500">
                        <strong>Stake:</strong> {bet.amount} points
                    </p>
                </div>

                {/* Proof content */}
                <div className="bg-white rounded-2xl shadow-lg border-2 border-gray-100 p-6 mb-6">
                    <h3 className="text-lg font-bold text-gray-800 mb-4">📎 Uploaded Proof</h3>

                    {/* Proof comment */}
                    {bet.proof_comment && (
                        <div className="bg-gray-50 rounded-xl p-4 mb-4">
                            <p className="text-sm text-gray-500 font-semibold mb-1">Creator's comment:</p>
                            <p className="text-gray-800">{bet.proof_comment}</p>
                        </div>
                    )}

                    {/* Proof media */}
                    {bet.proof_media_url && (
                        <div className="rounded-xl overflow-hidden border border-gray-200">
                            {isVideo(bet.proof_media_url) ? (
                                <video
                                    src={`${API_BASE_URL}${bet.proof_media_url}`}
                                    controls
                                    className="w-full max-h-96 object-contain bg-black"
                                />
                            ) : (
                                <img
                                    src={`${API_BASE_URL}${bet.proof_media_url}`}
                                    alt="Proof"
                                    className="w-full max-h-96 object-contain bg-gray-100"
                                />
                            )}
                        </div>
                    )}

                    {!bet.proof_comment && !bet.proof_media_url && (
                        <p className="text-gray-400 text-center py-8">No proof uploaded yet.</p>
                    )}
                </div>

                {/* Vote section — only for challengers who haven't voted yet */}
                {isChallenger && bet.status === 'proof_under_review' && !hasVoted && (
                    <div className="bg-white rounded-2xl shadow-lg border-2 border-gray-100 p-6 mb-6">
                        <h3 className="text-lg font-bold text-gray-800 mb-4">Cast your vote</h3>
                        <p className="text-sm text-gray-500 mb-6">
                            Did the creator genuinely complete their commitment?
                        </p>

                        {confirmVote ? (
                            /* Confirmation step */
                            <div className="text-center">
                                <p className="text-gray-800 font-semibold mb-4">
                                    Are you sure you want to vote <span className={confirmVote === 'cool' ? 'text-green-600' : 'text-red-600'}>
                                        {confirmVote === 'cool' ? '👍 COOL' : '👎 NOT COOL'}
                                    </span>?
                                </p>
                                <div className="flex gap-3 justify-center">
                                    <button
                                        onClick={() => handleVote(confirmVote)}
                                        disabled={voting}
                                        className={`px-6 py-3 rounded-xl font-bold text-white transition-all ${confirmVote === 'cool'
                                            ? 'bg-green-500 hover:bg-green-600'
                                            : 'bg-red-500 hover:bg-red-600'
                                            } ${voting ? 'opacity-50 cursor-not-allowed' : ''}`}
                                    >
                                        {voting ? 'Submitting...' : 'Confirm'}
                                    </button>
                                    <button
                                        onClick={() => setConfirmVote(null)}
                                        className="px-6 py-3 rounded-xl font-bold text-gray-600 bg-gray-100 hover:bg-gray-200 transition-all"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        ) : (
                            /* Vote buttons */
                            <div className="flex gap-4">
                                <button
                                    onClick={() => setConfirmVote('cool')}
                                    className="flex-1 py-4 bg-green-50 border-2 border-green-200 text-green-700 rounded-xl font-bold text-lg hover:bg-green-100 hover:border-green-300 transition-all hover:shadow-md"
                                >
                                    👍 COOL
                                </button>
                                <button
                                    onClick={() => setConfirmVote('not_cool')}
                                    className="flex-1 py-4 bg-red-50 border-2 border-red-200 text-red-700 rounded-xl font-bold text-lg hover:bg-red-100 hover:border-red-300 transition-all hover:shadow-md"
                                >
                                    👎 NOT COOL
                                </button>
                            </div>
                        )}
                    </div>
                )}

                {/* Already voted message */}
                {hasVoted && (
                    <div className="bg-white rounded-2xl shadow-lg border-2 border-gray-100 p-6 mb-6 text-center">
                        <p className="text-gray-600 font-semibold">
                            You voted <span className={myVote?.vote === 'cool' ? 'text-green-600' : 'text-red-600'}>
                                {myVote?.vote === 'cool' ? '👍 COOL' : '👎 NOT COOL'}
                            </span>
                        </p>
                    </div>
                )}

                {/* Vote result toast */}
                {voteResult && (
                    <div className={`rounded-xl p-4 mb-6 text-center font-semibold ${voteResult.bet_status === 'won' ? 'bg-green-50 text-green-700 border-2 border-green-200' :
                        voteResult.bet_status === 'lost' ? 'bg-red-50 text-red-700 border-2 border-red-200' :
                            'bg-blue-50 text-blue-700 border-2 border-blue-200'
                        }`}>
                        {voteResult.bet_status === 'won' && '🎉 Bet resolved — Creator wins!'}
                        {voteResult.bet_status === 'lost' && '❌ Bet resolved — Creator loses!'}
                        {voteResult.bet_status === 'proof_under_review' && `Vote recorded! (${voteResult.cool_count}/${voteResult.total_voters} COOL so far)`}
                    </div>
                )}

                {/* Votes list */}
                {bet.proof_votes && bet.proof_votes.length > 0 && (
                    <div className="bg-white rounded-2xl shadow-lg border-2 border-gray-100 p-6">
                        <h3 className="text-lg font-bold text-gray-800 mb-4">
                            Votes ({totalVotes}/{totalVoters})
                        </h3>
                        <div className="space-y-3">
                            {bet.proof_votes.map(v => (
                                <div
                                    key={v.id}
                                    className={`flex items-center justify-between p-3 rounded-xl ${v.vote === 'cool' ? 'bg-green-50' : 'bg-red-50'
                                        }`}
                                >
                                    <span className="font-semibold text-gray-800">@{v.username}</span>
                                    <span className={`font-bold ${v.vote === 'cool' ? 'text-green-600' : 'text-red-600'}`}>
                                        {v.vote === 'cool' ? '👍 COOL' : '👎 NOT COOL'}
                                    </span>
                                </div>
                            ))}
                        </div>
                        {/* Remaining voters */}
                        {totalVoters > totalVotes && (
                            <p className="text-sm text-gray-400 mt-3 text-center">
                                Waiting for {totalVoters - totalVotes} more vote{totalVoters - totalVotes > 1 ? 's' : ''}...
                            </p>
                        )}
                    </div>
                )}

                {/* Error display */}
                {error && (
                    <div className="bg-red-50 border-2 border-red-200 rounded-xl p-4 text-red-700 text-center font-semibold mt-4">
                        {error}
                    </div>
                )}
            </div>
        </div>
    )
}
