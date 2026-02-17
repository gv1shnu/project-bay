/**
 * AdminPage.tsx — Admin dashboard for viewing all users and bets.
 *
 * Features:
 *   - Two oval toggle buttons: "Users" and "Bets"
 *   - Users view: table of all users with username, email, points, join date
 *   - Bets view: table of all bets with title, creator, stake, status, deadline, and challenges
 *   - Back to feed navigation
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiService } from '../services/api'
import { User, Bet } from '../types'

type Tab = 'users' | 'bets'

export default function AdminPage() {
    const navigate = useNavigate()
    const [activeTab, setActiveTab] = useState<Tab>('users')
    const [users, setUsers] = useState<User[]>([])
    const [bets, setBets] = useState<Bet[]>([])
    const [loading, setLoading] = useState(false)

    // ── Passphrase gate ──
    const [passphrase, setPassphrase] = useState('')          // Verified passphrase (stored after successful check)
    const [passphraseInput, setPassphraseInput] = useState('') // Current input value
    const [passphraseError, setPassphraseError] = useState('')
    const [verifying, setVerifying] = useState(false)
    const [authenticated, setAuthenticated] = useState(false)  // Whether passphrase has been verified

    const handlePassphraseSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setVerifying(true)
        setPassphraseError('')
        const res = await apiService.verifyAdminPassphrase(passphraseInput)
        if (res.data) {
            setPassphrase(passphraseInput)
            setAuthenticated(true)
        } else {
            setPassphraseError('Invalid passphrase')
        }
        setVerifying(false)
    }

    // Fetch data when tab changes (only after authentication)
    useEffect(() => {
        if (authenticated) fetchData()
    }, [activeTab, authenticated])

    const fetchData = async () => {
        setLoading(true)
        if (activeTab === 'users') {
            const res = await apiService.getAdminUsers(passphrase)
            if (res.data) setUsers(res.data)
        } else {
            const res = await apiService.getAdminBets(passphrase)
            if (res.data) setBets(res.data)
        }
        setLoading(false)
    }

    /** Status badge color mapping */
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'won': return 'bg-green-100 text-green-700'
            case 'lost': return 'bg-red-100 text-red-700'
            case 'cancelled': return 'bg-gray-100 text-gray-600'
            case 'active': return 'bg-yellow-100 text-yellow-700'
            case 'accepted': return 'bg-green-100 text-green-700'
            case 'pending': return 'bg-yellow-100 text-yellow-700'
            case 'rejected': return 'bg-red-100 text-red-700'
            default: return 'bg-gray-100 text-gray-600'
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-competitive-light/20 via-white to-friendly-light/20">
            <div className="container mx-auto px-4 py-8 max-w-6xl">
                {/* ── Back button ── */}
                <button
                    onClick={() => navigate('/')}
                    className="mb-6 flex items-center gap-2 text-gray-600 hover:text-gray-800 transition-colors"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    Back to Feed
                </button>

                {/* ── Passphrase Gate ── */}
                {!authenticated ? (
                    <div className="flex items-center justify-center min-h-[60vh]">
                        <form onSubmit={handlePassphraseSubmit} className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-sm text-center">
                            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <svg className="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                </svg>
                            </div>
                            <h2 className="text-xl font-bold text-gray-800 mb-1">Admin Access</h2>
                            <p className="text-sm text-gray-500 mb-6">Enter the admin passphrase to continue</p>
                            <input
                                type="password"
                                value={passphraseInput}
                                onChange={(e) => setPassphraseInput(e.target.value)}
                                placeholder="Passphrase"
                                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-center text-lg tracking-widest focus:outline-none focus:border-competitive-DEFAULT transition-colors mb-3"
                                autoFocus
                            />
                            {passphraseError && (
                                <p className="text-red-500 text-sm mb-3">{passphraseError}</p>
                            )}
                            <button
                                type="submit"
                                disabled={verifying || !passphraseInput}
                                className="w-full py-3 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-xl font-semibold hover:from-competitive-DEFAULT hover:to-competitive-light transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {verifying ? 'Verifying...' : 'Unlock'}
                            </button>
                        </form>
                    </div>
                ) : (
                    <>
                        {/* ── Header ── */}
                        <div className="text-center mb-8">
                            <h1 className="text-4xl font-bold bg-gradient-to-r from-competitive-dark to-friendly-dark bg-clip-text text-transparent mb-2">
                                Admin Dashboard
                            </h1>
                            <p className="text-gray-500">Overview of all platform data</p>
                        </div>

                        {/* ── Oval Toggle Buttons ── */}
                        <div className="flex justify-center gap-4 mb-8">
                            <button
                                onClick={() => setActiveTab('users')}
                                className={`px-8 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 shadow-sm ${activeTab === 'users'
                                    ? 'bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white shadow-md scale-105'
                                    : 'bg-white text-gray-600 border-2 border-gray-200 hover:border-competitive-light hover:text-competitive-dark'
                                    }`}
                            >
                                Users
                            </button>
                            <button
                                onClick={() => setActiveTab('bets')}
                                className={`px-8 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 shadow-sm ${activeTab === 'bets'
                                    ? 'bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white shadow-md scale-105'
                                    : 'bg-white text-gray-600 border-2 border-gray-200 hover:border-competitive-light hover:text-competitive-dark'
                                    }`}
                            >
                                Bets
                            </button>
                        </div>

                        {/* ── Content Panel ── */}
                        <div className="bg-white rounded-2xl shadow-lg p-6">
                            {loading ? (
                                <div className="text-center py-16">
                                    <p className="text-gray-500 text-lg">Loading...</p>
                                </div>
                            ) : activeTab === 'users' ? (
                                /* ═══════ Users Table ═══════ */
                                <>
                                    <div className="flex justify-between items-center mb-6">
                                        <h2 className="text-xl font-bold text-gray-800">All Users</h2>
                                        <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                                            {users.length} total
                                        </span>
                                    </div>
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left">
                                            <thead>
                                                <tr className="border-b-2 border-gray-100">
                                                    <th className="pb-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">ID</th>
                                                    <th className="pb-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Username</th>
                                                    <th className="pb-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Email</th>
                                                    <th className="pb-3 text-xs font-semibold text-gray-400 uppercase tracking-wider text-right">Points</th>
                                                    <th className="pb-3 text-xs font-semibold text-gray-400 uppercase tracking-wider text-right">Joined</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {users.map((user) => (
                                                    <tr
                                                        key={user.id}
                                                        className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors"
                                                    >
                                                        <td className="py-4 text-sm text-gray-400 font-mono">{user.id}</td>
                                                        <td className="py-4">
                                                            <span
                                                                className="font-semibold text-gray-800 cursor-pointer hover:text-competitive-dark transition-colors"
                                                                onClick={() => navigate(`/profile/${user.username}`)}
                                                            >
                                                                @{user.username}
                                                            </span>
                                                        </td>
                                                        <td className="py-4 text-sm text-gray-500">{user.email}</td>
                                                        <td className="py-4 text-right">
                                                            <span className="font-semibold text-competitive-dark">{user.points}</span>
                                                            <span className="text-xs text-gray-400 ml-1">pts</span>
                                                        </td>
                                                        <td className="py-4 text-sm text-gray-400 text-right">
                                                            {user.created_at
                                                                ? new Date(user.created_at).toLocaleDateString()
                                                                : '—'}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </>
                            ) : (
                                /* ═══════ Bets Table ═══════ */
                                <>
                                    <div className="flex justify-between items-center mb-6">
                                        <h2 className="text-xl font-bold text-gray-800">All Bets</h2>
                                        <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                                            {bets.length} total
                                        </span>
                                    </div>
                                    <div className="space-y-4">
                                        {bets.map((bet) => (
                                            <div
                                                key={bet.id}
                                                className="border border-gray-100 rounded-xl p-5 hover:shadow-md transition-shadow"
                                            >
                                                {/* Top row: title + status badge */}
                                                <div className="flex justify-between items-start mb-3">
                                                    <div className="flex-1">
                                                        <h3 className="font-semibold text-gray-800 text-lg">{bet.title}</h3>
                                                        <p className="text-sm text-gray-500 mt-0.5">
                                                            by <span className="font-medium text-gray-700">@{bet.username}</span>
                                                        </p>
                                                    </div>
                                                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ml-3 ${getStatusColor(bet.status)}`}>
                                                        {bet.status.toUpperCase()}
                                                    </span>
                                                </div>

                                                {/* Info row */}
                                                <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-500 mb-3">
                                                    <span>
                                                        Stake: <span className="font-semibold text-competitive-dark">{bet.amount} pts</span>
                                                    </span>
                                                    <span>
                                                        Criteria: <span className="text-gray-600">{bet.criteria}</span>
                                                    </span>
                                                    {bet.deadline && (
                                                        <span>
                                                            Deadline: <span className="text-gray-600">
                                                                {new Date(bet.deadline).toLocaleDateString()}
                                                            </span>
                                                        </span>
                                                    )}
                                                    {bet.created_at && (
                                                        <span>
                                                            Created: <span className="text-gray-600">
                                                                {new Date(bet.created_at).toLocaleDateString()}
                                                            </span>
                                                        </span>
                                                    )}
                                                </div>

                                                {/* Challenges */}
                                                {bet.challenges && bet.challenges.length > 0 && (
                                                    <div className="mt-3 pt-3 border-t border-gray-100">
                                                        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                                                            Challenges ({bet.challenges.length})
                                                        </p>
                                                        <div className="flex flex-wrap gap-2">
                                                            {bet.challenges.map((c) => (
                                                                <div
                                                                    key={c.id}
                                                                    className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-1.5 text-sm"
                                                                >
                                                                    <span className="font-medium text-gray-700">
                                                                        @{c.challenger_username}
                                                                    </span>
                                                                    <span className="text-gray-400">·</span>
                                                                    <span className="font-semibold text-competitive-dark">
                                                                        {c.amount} pts
                                                                    </span>
                                                                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${getStatusColor(c.status)}`}>
                                                                        {c.status.toUpperCase()}
                                                                    </span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        ))}

                                        {bets.length === 0 && (
                                            <div className="text-center py-16">
                                                <p className="text-gray-500">No bets in the system yet.</p>
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                    </>
                )}
            </div>
        </div>
    )
}
