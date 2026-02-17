/**
 * NotificationsPage.tsx — Displays the user's notifications.
 *
 * Shows activity related to the user's bets and challenges:
 *   - Challenge received / accepted / rejected
 *   - Bet deadline approaching
 *   - Proof upload reminders
 *   - Bet resolution results
 *
 * Redirects to login if not authenticated.
 */
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { getAvatarUrl } from '../utils/avatar'

export default function NotificationsPage() {
    const { user, isAuthenticated } = useAuth()
    const navigate = useNavigate()

    // Redirect to login if not signed in
    useEffect(() => {
        if (!isAuthenticated) {
            navigate('/login')
        }
    }, [isAuthenticated, navigate])

    if (!user) return null

    return (
        <div className="min-h-screen bg-gradient-to-br from-competitive-light/20 via-white to-friendly-light/20">
            <div className="container mx-auto px-4 py-8 max-w-2xl">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => navigate('/')}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                            aria-label="Back to home"
                        >
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                            </svg>
                        </button>
                        <h1 className="text-3xl font-bold bg-gradient-to-r from-competitive-dark to-friendly-dark bg-clip-text text-transparent">
                            Notifications
                        </h1>
                    </div>
                    <div className="flex items-center gap-3">
                        <a href={`/profile/${user.username}`} className="hover:opacity-80 transition-opacity">
                            <img
                                src={getAvatarUrl(user.username)}
                                alt={user.username}
                                className="w-9 h-9 rounded-full border-2 border-competitive-light"
                            />
                        </a>
                    </div>
                </div>

                {/* Empty state — shown until backend notifications are wired up */}
                <div className="bg-white rounded-2xl shadow-lg border-2 border-gray-100 p-12 text-center">
                    <div className="text-6xl mb-4">🔔</div>
                    <h2 className="text-xl font-bold text-gray-800 mb-2">No notifications yet</h2>
                    <p className="text-gray-500 mb-6">
                        When someone challenges your bet, or a bet you're involved in updates, you'll see it here.
                    </p>
                    <button
                        onClick={() => navigate('/')}
                        className="px-6 py-3 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-lg font-semibold hover:from-competitive-DEFAULT hover:to-competitive-light transition-all shadow-md hover:shadow-lg"
                    >
                        Browse Bets
                    </button>
                </div>
            </div>
        </div>
    )
}
