/**
 * NotificationsPage.tsx — Displays the user's notifications.
 *
 * Shows activity related to the user's bets and challenges:
 *   - Proof uploaded for a bet you challenged
 *   - (future: challenge received, bet resolved, etc.)
 *
 * Redirects to login if not authenticated.
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { apiService } from '../services/api'
import { Notification } from '../types'
import { getAvatarUrl } from '../utils/avatar'

export default function NotificationsPage() {
    const { user, isAuthenticated } = useAuth()
    const navigate = useNavigate()
    const [notifications, setNotifications] = useState<Notification[]>([])
    const [loading, setLoading] = useState(true)

    // Redirect to login if not signed in
    useEffect(() => {
        if (!isAuthenticated) {
            navigate('/login')
        }
    }, [isAuthenticated, navigate])

    // Fetch notifications on mount
    useEffect(() => {
        if (isAuthenticated) fetchNotifications()
    }, [isAuthenticated])

    const fetchNotifications = async () => {
        setLoading(true)
        const response = await apiService.getNotifications()
        if (response.data) {
            setNotifications(response.data)
        }
        setLoading(false)
    }

    /** Mark a single notification as read (locally + server) */
    const handleMarkRead = async (id: number) => {
        await apiService.markNotificationRead(id)
        setNotifications(prev =>
            prev.map(n => (n.id === id ? { ...n, is_read: 1 } : n))
        )
    }

    /** Mark all as read */
    const handleMarkAllRead = async () => {
        await apiService.markAllNotificationsRead()
        setNotifications(prev => prev.map(n => ({ ...n, is_read: 1 })))
    }

    /** Format relative time (e.g. "2m ago", "3h ago") */
    const timeAgo = (dateStr: string) => {
        const diff = Date.now() - new Date(dateStr).getTime()
        const mins = Math.floor(diff / 60000)
        if (mins < 1) return 'just now'
        if (mins < 60) return `${mins}m ago`
        const hrs = Math.floor(mins / 60)
        if (hrs < 24) return `${hrs}h ago`
        const days = Math.floor(hrs / 24)
        return `${days}d ago`
    }

    if (!user) return null

    const unreadCount = notifications.filter(n => n.is_read === 0).length

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
                        {unreadCount > 0 && (
                            <span className="px-2.5 py-0.5 text-xs font-bold bg-red-500 text-white rounded-full">
                                {unreadCount}
                            </span>
                        )}
                    </div>
                    <div className="flex items-center gap-3">
                        {unreadCount > 0 && (
                            <button
                                onClick={handleMarkAllRead}
                                className="text-sm text-competitive-dark hover:underline font-semibold"
                            >
                                Mark all as read
                            </button>
                        )}
                        <a href={`/profile/${user.username}`} className="hover:opacity-80 transition-opacity">
                            <img
                                src={getAvatarUrl(user.username)}
                                alt={user.username}
                                className="w-9 h-9 rounded-full border-2 border-competitive-light"
                            />
                        </a>
                    </div>
                </div>

                {/* Notifications list */}
                {loading ? (
                    <div className="text-center py-20">
                        <p className="text-gray-500 text-lg">Loading notifications...</p>
                    </div>
                ) : notifications.length === 0 ? (
                    /* Empty state */
                    <div className="bg-white rounded-2xl shadow-lg border-2 border-gray-100 p-12 text-center">
                        <div className="text-6xl mb-4">🔔</div>
                        <h2 className="text-xl font-bold text-gray-800 mb-2">No notifications yet</h2>
                        <p className="text-gray-500 mb-6">
                            When someone uploads proof for a bet you challenged, you'll see it here.
                        </p>
                        <button
                            onClick={() => navigate('/')}
                            className="px-6 py-3 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-lg font-semibold hover:from-competitive-DEFAULT hover:to-competitive-light transition-all shadow-md hover:shadow-lg"
                        >
                            Browse Bets
                        </button>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {notifications.map(notif => (
                            <div
                                key={notif.id}
                                className={`bg-white rounded-xl shadow-sm border-2 p-4 flex items-start gap-4 transition-all hover:shadow-md cursor-pointer ${notif.is_read === 0
                                    ? 'border-competitive-light/60 bg-competitive-light/5'
                                    : 'border-gray-100'
                                    }`}
                                onClick={() => {
                                    if (notif.is_read === 0) handleMarkRead(notif.id)
                                    if (notif.bet_id) navigate(`/bets/${notif.bet_id}/proof`)
                                }}
                            >
                                {/* Unread indicator dot */}
                                <div className="pt-1.5">
                                    {notif.is_read === 0 ? (
                                        <span className="block w-2.5 h-2.5 bg-red-500 rounded-full" />
                                    ) : (
                                        <span className="block w-2.5 h-2.5 bg-transparent rounded-full" />
                                    )}
                                </div>
                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                    <p className={`text-sm ${notif.is_read === 0 ? 'text-gray-900 font-semibold' : 'text-gray-600'}`}>
                                        {notif.message}
                                    </p>
                                    <p className="text-xs text-gray-400 mt-1">{timeAgo(notif.created_at)}</p>
                                </div>
                                {/* Bell icon */}
                                <div className="text-gray-300 pt-0.5">
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                                    </svg>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
