/**
 * ProfilePage.tsx — User profile page.
 *
 * Shows a user's profile (own or others') with:
 *   - Avatar, username, points, join date
 *   - Created bets stats (total / won / lost / active)
 *   - Challenged bets stats (total / won / lost / pending)
 *   - List of all bets the user created (with cancel option for own active bets)
 *   - List of all challenges the user made (with win/loss indicators)
 *   - "Add Friend" placeholder button (feature coming soon)
 *   - Floating "+" button to create new bets
 *
 * Data source: Fetches ALL public bets, then filters for the profile user.
 * Challenge win/loss is determined by cross-referencing challenge status with bet status:
 *   - Challenger wins when the BET is "lost" (creator failed their commitment)
 *   - Challenger loses when the BET is "won" (creator succeeded)
 */
import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { apiService } from '../services/api'
import { Bet } from '../types'
import { getAvatarUrl } from '../utils/avatar'
import CreateBetModal from '../components/CreateBetModal'
import AuthPrompt from '../components/AuthPrompt'

export default function ProfilePage() {
    // Get username from URL params (e.g., /profile/johndoe)
    const { username } = useParams<{ username: string }>()
    const { user } = useAuth()
    const navigate = useNavigate()

    // ── State ──
    const [userBets, setUserBets] = useState<Bet[]>([])  // Bets created by this user
    // Challenges this user made against other people's bets
    const [userChallenges, setUserChallenges] = useState<{ bet: Bet, challenge: { id: number, amount: number, status: string, created_at: string } }[]>([])
    const [loading, setLoading] = useState(true)
    const [createdStats, setCreatedStats] = useState({ total: 0, won: 0, lost: 0, active: 0 })
    const [challengedStats, setChallengedStats] = useState({ total: 0, won: 0, lost: 0, pending: 0 })
    const [profileUser, setProfileUser] = useState<{ points: number; created_at: string } | null>(null)
    const [showCreateBet, setShowCreateBet] = useState(false)
    const [showAuthPrompt, setShowAuthPrompt] = useState(false)

    // Is the logged-in user viewing their own profile?
    const isOwnProfile = user?.username === username

    // Re-fetch data when the username in the URL changes
    useEffect(() => {
        fetchUserData()
    }, [username])

    /**
     * Fetch all profile data: user info, their bets, and their challenges.
     * Strategy: fetch ALL public bets, then filter client-side for this user.
     * Not ideal for scaling, but works fine for current user count.
     */
    const fetchUserData = async () => {
        setLoading(true)

        // 1. Fetch user profile (points, join date)
        if (username) {
            const profileResponse = await apiService.getUserProfile(username)
            if (profileResponse.data) {
                setProfileUser({
                    points: profileResponse.data.points,
                    created_at: profileResponse.data.created_at
                })
            }
        }

        // 2. Fetch all public bets and filter for this user
        const response = await apiService.getPublicBets()
        if (response.data) {
            // ── Created bets: bets where this user is the creator ──
            const createdBets = response.data.filter((bet: Bet) => bet.username === username)
            setUserBets(createdBets)

            // Calculate created bet stats
            setCreatedStats({
                total: createdBets.length,
                won: createdBets.filter((b: Bet) => b.status === 'won').length,
                lost: createdBets.filter((b: Bet) => b.status === 'lost').length,
                active: createdBets.filter((b: Bet) => b.status === 'active').length
            })

            // ── Challenged bets: challenges this user made on other people's bets ──
            const challengesList: { bet: Bet, challenge: { id: number, amount: number, status: string, created_at: string } }[] = []
            let challengeTotal = 0, challengeWon = 0, challengeLost = 0, challengePending = 0

            response.data.forEach((bet: Bet) => {
                if (bet.challenges) {
                    // Find challenges made by this profile user
                    bet.challenges.filter(c => c.challenger_username === username).forEach(c => {
                        challengesList.push({ bet, challenge: { id: c.id, amount: c.amount, status: c.status, created_at: c.created_at } })
                        challengeTotal++
                        if (c.status === 'accepted') {
                            // Determine outcome by checking the BET's status:
                            // Challenger wins when bet is LOST (creator failed)
                            // Challenger loses when bet is WON (creator succeeded)
                            if (bet.status === 'lost') challengeWon++
                            else if (bet.status === 'won') challengeLost++
                            else challengePending++  // Bet still active
                        } else if (c.status === 'pending') {
                            challengePending++
                        }
                    })
                }
            })
            setUserChallenges(challengesList)

            setChallengedStats({
                total: challengeTotal,
                won: challengeWon,
                lost: challengeLost,
                pending: challengePending
            })
        }
        setLoading(false)
    }

    /** Map bet status to Tailwind color classes for status badges */
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'won': return 'bg-green-100 text-green-700'
            case 'lost': return 'bg-red-100 text-red-700'
            case 'cancelled': return 'bg-gray-100 text-gray-700'
            default: return 'bg-yellow-100 text-yellow-700'  // active
        }
    }

    /** Cancel a bet — confirms with user, then calls API to cancel and refund all stakes */
    const handleCancelBet = async (betId: number) => {
        if (confirm('Are you sure you want to cancel this bet? All stakes will be refunded.')) {
            const response = await apiService.updateBetStatus(betId, 'cancelled')
            if (response.data) {
                await fetchUserData()  // Refresh profile data
            } else {
                alert(response.error || 'Failed to cancel bet')
            }
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-competitive-light/20 via-white to-friendly-light/20">
            <div className="container mx-auto px-4 py-8 max-w-4xl">
                {/* ── Back to feed button ── */}
                <button
                    onClick={() => navigate('/')}
                    className="mb-6 flex items-center gap-2 text-gray-600 hover:text-gray-800 transition-colors"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    Back to Feed
                </button>

                {/* ══════════════ Profile Header ══════════════ */}
                <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
                    <div className="flex flex-col md:flex-row items-center gap-6">
                        {/* Large avatar */}
                        <img
                            src={getAvatarUrl(username || '')}
                            alt={`${username}'s avatar`}
                            className="w-32 h-32 rounded-full border-4 border-competitive-light shadow-lg"
                        />
                        <div className="text-center md:text-left flex-1">
                            <h1 className="text-3xl font-bold text-gray-800 mb-2">@{username}</h1>
                            {/* Points and join date */}
                            {profileUser && (
                                <div className="mb-4">
                                    <p className="text-xl text-competitive-dark font-semibold">
                                        {profileUser.points} points
                                    </p>
                                    <p className="text-sm text-gray-500">
                                        Joined {new Date(profileUser.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                                    </p>
                                </div>
                            )}

                            {/* ── Created Bets Stats Row ── */}
                            <div className="mb-4">
                                <p className="text-sm font-semibold text-gray-600 mb-2">Bets Created</p>
                                <div className="flex flex-wrap justify-center md:justify-start gap-3">
                                    <div className="bg-gray-100 rounded-lg px-3 py-2">
                                        <p className="text-xl font-bold text-gray-800">{createdStats.total}</p>
                                        <p className="text-xs text-gray-500 uppercase">Total</p>
                                    </div>
                                    <div className="bg-green-50 rounded-lg px-3 py-2">
                                        <p className="text-xl font-bold text-green-600">{createdStats.won}</p>
                                        <p className="text-xs text-green-500 uppercase">Won</p>
                                    </div>
                                    <div className="bg-red-50 rounded-lg px-3 py-2">
                                        <p className="text-xl font-bold text-red-600">{createdStats.lost}</p>
                                        <p className="text-xs text-red-500 uppercase">Lost</p>
                                    </div>
                                    <div className="bg-yellow-50 rounded-lg px-3 py-2">
                                        <p className="text-xl font-bold text-yellow-600">{createdStats.active}</p>
                                        <p className="text-xs text-yellow-500 uppercase">Active</p>
                                    </div>
                                </div>
                            </div>

                            {/* ── Challenged Bets Stats Row ── */}
                            <div>
                                <p className="text-sm font-semibold text-gray-600 mb-2">Bets Challenged</p>
                                <div className="flex flex-wrap justify-center md:justify-start gap-3">
                                    <div className="bg-purple-50 rounded-lg px-3 py-2">
                                        <p className="text-xl font-bold text-purple-600">{challengedStats.total}</p>
                                        <p className="text-xs text-purple-500 uppercase">Total</p>
                                    </div>
                                    <div className="bg-green-50 rounded-lg px-3 py-2">
                                        <p className="text-xl font-bold text-green-600">{challengedStats.won}</p>
                                        <p className="text-xs text-green-500 uppercase">Won</p>
                                    </div>
                                    <div className="bg-red-50 rounded-lg px-3 py-2">
                                        <p className="text-xl font-bold text-red-600">{challengedStats.lost}</p>
                                        <p className="text-xs text-red-500 uppercase">Lost</p>
                                    </div>
                                    <div className="bg-blue-50 rounded-lg px-3 py-2">
                                        <p className="text-xl font-bold text-blue-600">{challengedStats.pending}</p>
                                        <p className="text-xs text-blue-500 uppercase">Pending</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* ── Add Friend button (placeholder — only shown on other users' profiles) ── */}
                        {!isOwnProfile && user && (
                            <div className="text-center">
                                <button
                                    onClick={() => alert('Friend feature coming soon!')}
                                    className="px-6 py-3 bg-gradient-to-r from-friendly-dark to-friendly-DEFAULT text-white rounded-lg font-semibold hover:from-friendly-DEFAULT hover:to-friendly-light transition-all shadow-md hover:shadow-lg"
                                >
                                    Add Friend
                                </button>
                                <p className="text-sm text-gray-500 mt-2">0 friends</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* ══════════════ Created Bets List ══════════════ */}
                <div className="bg-white rounded-2xl shadow-lg p-6">
                    <h2 className="text-xl font-bold text-gray-800 mb-6">
                        {isOwnProfile ? 'Your Bets' : `${username}'s Bets`}
                    </h2>

                    {loading ? (
                        <div className="text-center py-12">
                            <p className="text-gray-500">Loading bets...</p>
                        </div>
                    ) : userBets.length === 0 ? (
                        <div className="text-center py-12">
                            <p className="text-gray-500">No bets yet.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {userBets.map((bet) => (
                                <div
                                    key={bet.id}
                                    className="border border-gray-100 rounded-xl p-4 hover:shadow-md transition-shadow"
                                >
                                    {/* Bet title + status badge */}
                                    <div className="flex justify-between items-start mb-2">
                                        <h3 className="font-semibold text-gray-800">{bet.title}</h3>
                                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(bet.status)}`}>
                                            {bet.status.toUpperCase()}
                                        </span>
                                    </div>
                                    <p className="text-sm text-gray-600 mb-2">{bet.criteria}</p>
                                    {/* Stakes and date info */}
                                    <div className="flex justify-between items-center text-sm text-gray-500">
                                        <div className="flex gap-4">
                                            <span className="font-semibold text-gray-600">
                                                Author stake: {bet.amount} pts
                                            </span>
                                            <span className="font-semibold text-competitive-dark">
                                                {/* Total = author stake + all non-rejected challenger stakes */}
                                                Total: {bet.amount + (bet.challenges?.filter(c => c.status !== 'rejected').reduce((sum, c) => sum + c.amount, 0) || 0)} pts
                                                {/* Show winnings/losses indicator for resolved bets */}
                                                {bet.status === 'won' && <span className="text-green-600 ml-1">(+{bet.challenges?.filter(c => c.status === 'accepted').reduce((sum, c) => sum + c.amount, 0) || 0})</span>}
                                                {bet.status === 'lost' && <span className="text-red-600 ml-1">(-{bet.amount})</span>}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <span>{new Date(bet.created_at).toLocaleDateString()}</span>
                                            {/* Cancel button — only on own active bets before deadline */}
                                            {isOwnProfile && bet.status === 'active' && new Date() < new Date(bet.deadline) && (
                                                <button
                                                    onClick={() => handleCancelBet(bet.id)}
                                                    className="px-3 py-1 bg-red-100 text-red-600 rounded-lg text-xs font-semibold hover:bg-red-200 transition-colors"
                                                >
                                                    Cancel
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* ══════════════ Challenges List ══════════════ */}
                <div className="bg-white rounded-2xl shadow-lg p-6 mt-6">
                    <h2 className="text-xl font-bold text-gray-800 mb-6">
                        {isOwnProfile ? 'Your Challenges' : `${username}'s Challenges`}
                    </h2>

                    {loading ? (
                        <div className="text-center py-12">
                            <p className="text-gray-500">Loading challenges...</p>
                        </div>
                    ) : userChallenges.length === 0 ? (
                        <div className="text-center py-12">
                            <p className="text-gray-500">No challenges yet.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {userChallenges.map(({ bet, challenge }) => (
                                <div
                                    key={challenge.id}
                                    className="border border-purple-100 rounded-xl p-4 hover:shadow-md transition-shadow"
                                >
                                    {/* Challenge info: bet title + challenge status */}
                                    <div className="flex justify-between items-start mb-2">
                                        <div>
                                            <h3 className="font-semibold text-gray-800">{bet.title}</h3>
                                            <p className="text-sm text-gray-500">by @{bet.username}</p>
                                        </div>
                                        {/* Challenge status badge with color coding */}
                                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${challenge.status === 'accepted' ? 'bg-green-100 text-green-700' :
                                                challenge.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                                                    challenge.status === 'cancelled' ? 'bg-gray-100 text-gray-700' :
                                                        'bg-red-100 text-red-700'  // rejected
                                            }`}>
                                            {challenge.status.toUpperCase()}
                                        </span>
                                    </div>
                                    {/* Stake amount and outcome */}
                                    <div className="flex justify-between text-sm text-gray-500">
                                        <span className="font-semibold text-purple-600">
                                            Staked {challenge.amount} pts
                                            {/* Outcome indicators — shown only for resolved bets */}
                                            {bet.status === 'lost' && <span className="text-green-600 ml-1">(Won!)</span>}
                                            {bet.status === 'won' && <span className="text-red-600 ml-1">(Lost)</span>}
                                        </span>
                                        <span>{new Date(challenge.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Floating Action Button — Create Bet ── */}
            <button
                onClick={() => user ? setShowCreateBet(true) : setShowAuthPrompt(true)}
                className="fixed bottom-8 right-8 w-16 h-16 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-full shadow-lg hover:shadow-xl transition-all hover:scale-110 flex items-center justify-center text-3xl font-bold"
                title="Create a new bet"
            >
                +
            </button>

            {/* ── Modals ── */}
            {showAuthPrompt && (
                <AuthPrompt onClose={() => setShowAuthPrompt(false)} />
            )}
            {showCreateBet && (
                <CreateBetModal
                    onClose={() => setShowCreateBet(false)}
                    onSubmit={async (title, criteria, amount, deadline) => {
                        const response = await apiService.createBet(title, criteria, amount, deadline)
                        if (response.data) {
                            setShowCreateBet(false)
                            fetchUserData()  // Refresh profile data to show new bet
                        } else {
                            alert(response.error || 'Failed to create bet')
                        }
                    }}
                />
            )}
        </div>
    )
}