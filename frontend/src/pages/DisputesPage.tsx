/**
 * DisputesPage.tsx — The Tribunal (Level 2).
 *
 * Public feed of bets whose proof was disputed by a challenger. Any neutral
 * user (not the creator, not a challenger) can review the proof and vote.
 * The first side to reach a 3-vote majority decides the outcome.
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { apiService } from '../services/api'
import { Bet } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const MAJORITY = 3

export default function DisputesPage() {
    const navigate = useNavigate()
    const { user, isAuthenticated } = useAuth()

    const [disputes, setDisputes] = useState<Bet[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [votingId, setVotingId] = useState<number | null>(null)

    useEffect(() => {
        fetchDisputes()
    }, [])

    const fetchDisputes = async () => {
        setLoading(true)
        const response = await apiService.getDisputes()
        if (response.data) setDisputes(response.data)
        else setError(response.error || 'Failed to load disputes')
        setLoading(false)
    }

    const handleVote = async (betId: number, vote: 'cool' | 'not_cool') => {
        if (!isAuthenticated) {
            navigate('/login')
            return
        }
        setVotingId(betId)
        setError(null)
        const response = await apiService.voteOnDispute(betId, vote)
        if (response.error) setError(response.error)
        await fetchDisputes()
        setVotingId(null)
    }

    const isVideo = (url: string) => /\.(mp4|mov|webm)$/i.test(url)

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-competitive-light/20 via-white to-friendly-light/20 flex items-center justify-center">
                <p className="text-gray-500 text-lg">Loading disputes...</p>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-competitive-light/20 via-white to-friendly-light/20">
            <div className="container mx-auto px-4 py-8 max-w-2xl">
                {/* Header */}
                <div className="flex items-center gap-4 mb-2">
                    <button
                        onClick={() => navigate('/')}
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                        aria-label="Back to home"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                    </button>
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-competitive-dark to-friendly-dark bg-clip-text text-transparent">
                        The Tribunal
                    </h1>
                </div>
                <p className="text-sm text-gray-500 mb-8 ml-10">
                    Disputed proof, judged by the community. First side to {MAJORITY} votes wins — majority
                    jurors split a 5% court fee from the pot.
                </p>

                {error && (
                    <div className="bg-red-50 border-2 border-red-200 rounded-xl p-4 text-red-700 text-center font-semibold mb-6">
                        {error}
                    </div>
                )}

                {disputes.length === 0 && (
                    <div className="bg-white rounded-2xl shadow-lg border-2 border-gray-100 p-10 text-center">
                        <p className="text-gray-500 text-lg">No open disputes right now. ⚖️</p>
                        <p className="text-gray-400 text-sm mt-1">Check back later.</p>
                    </div>
                )}

                <div className="space-y-6">
                    {disputes.map(bet => {
                        const coolVotes = bet.jury_votes?.filter(v => v.vote === 'cool') ?? []
                        const notCoolVotes = bet.jury_votes?.filter(v => v.vote === 'not_cool') ?? []
                        const isCreator = bet.user_id === user?.id
                        const isChallenger = bet.challenges?.some(
                            c => c.challenger_id === user?.id && c.status === 'pending'
                        )
                        const alreadyVoted = bet.jury_votes?.some(v => v.user_id === user?.id)
                        const canVote = isAuthenticated && !isCreator && !isChallenger && !alreadyVoted

                        return (
                            <div key={bet.id} className="bg-white rounded-2xl shadow-lg border-2 border-gray-100 p-6">
                                <div className="flex items-center gap-2 mb-3">
                                    <span className="text-xs font-bold px-2 py-1 rounded-full bg-purple-100 text-purple-800">
                                        ⚖️ Disputed
                                    </span>
                                    <span className="text-xs text-gray-400">by @{bet.username}</span>
                                </div>
                                <h2 className="text-xl font-bold text-gray-800 mb-1">{bet.title}</h2>
                                <p className="text-sm text-gray-500 mb-1"><strong>Criteria:</strong> {bet.criteria}</p>
                                <p className="text-sm text-gray-500 mb-4"><strong>Stake:</strong> {bet.amount} points</p>

                                {/* Proof */}
                                {bet.proof_comment && (
                                    <div className="bg-gray-50 rounded-xl p-4 mb-4">
                                        <p className="text-sm text-gray-500 font-semibold mb-1">Creator's comment:</p>
                                        <p className="text-gray-800">{bet.proof_comment}</p>
                                    </div>
                                )}
                                {bet.proof_media_url && (
                                    <div className="rounded-xl overflow-hidden border border-gray-200 mb-4">
                                        {isVideo(bet.proof_media_url) ? (
                                            <video src={`${API_BASE_URL}${bet.proof_media_url}`} controls className="w-full max-h-96 object-contain bg-black" />
                                        ) : (
                                            <img src={`${API_BASE_URL}${bet.proof_media_url}`} alt="Proof" className="w-full max-h-96 object-contain bg-gray-100" />
                                        )}
                                    </div>
                                )}

                                {/* Tally */}
                                <div className="flex gap-3 mb-4">
                                    <div className="flex-1 text-center py-2 rounded-xl bg-green-50 border border-green-200">
                                        <p className="text-xs text-green-700 font-semibold">👍 Legit</p>
                                        <p className="text-lg font-bold text-green-700">{coolVotes.length}/{MAJORITY}</p>
                                    </div>
                                    <div className="flex-1 text-center py-2 rounded-xl bg-red-50 border border-red-200">
                                        <p className="text-xs text-red-700 font-semibold">👎 Fake</p>
                                        <p className="text-lg font-bold text-red-700">{notCoolVotes.length}/{MAJORITY}</p>
                                    </div>
                                </div>

                                {/* Vote actions */}
                                {canVote ? (
                                    <div className="flex gap-4">
                                        <button
                                            onClick={() => handleVote(bet.id, 'cool')}
                                            disabled={votingId === bet.id}
                                            className="flex-1 py-3 bg-green-50 border-2 border-green-200 text-green-700 rounded-xl font-bold hover:bg-green-100 transition-all disabled:opacity-50"
                                        >
                                            👍 Legit
                                        </button>
                                        <button
                                            onClick={() => handleVote(bet.id, 'not_cool')}
                                            disabled={votingId === bet.id}
                                            className="flex-1 py-3 bg-red-50 border-2 border-red-200 text-red-700 rounded-xl font-bold hover:bg-red-100 transition-all disabled:opacity-50"
                                        >
                                            👎 Fake
                                        </button>
                                    </div>
                                ) : (
                                    <p className="text-sm text-gray-400 text-center py-2">
                                        {!isAuthenticated ? 'Sign in to serve on the jury.'
                                            : isCreator ? "You can't judge your own bet."
                                                : isChallenger ? "You have a stake in this bet — you can't be a juror."
                                                    : 'You have already cast your juror vote.'}
                                    </p>
                                )}
                            </div>
                        )
                    })}
                </div>
            </div>
        </div>
    )
}
