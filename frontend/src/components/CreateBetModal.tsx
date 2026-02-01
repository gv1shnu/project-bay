import { useState, FormEvent, useEffect, MouseEvent } from 'react'
import { useAuth } from '../contexts/AuthContext'

interface CreateBetModalProps {
    onClose: () => void
    onSubmit: (title: string, criteria: string, amount: number) => void
    error?: any
    onClearError?: () => void
}

export default function CreateBetModal({ onClose, onSubmit, error, onClearError }: CreateBetModalProps) {
    const { isAuthenticated, user } = useAuth()
    const [title, setTitle] = useState('')
    const [criteria, setCriteria] = useState('')
    const [amount, setAmount] = useState('')
    const [localError, setLocalError] = useState('')

    useEffect(() => {
        document.body.style.overflow = 'hidden'
        return () => {
            document.body.style.overflow = 'unset'
        }
    }, [])

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault()
        setLocalError('')
        onClearError?.()

        if (!title.trim()) {
            setLocalError('Please enter a title for your bet')
            return
        }

        if (!criteria.trim()) {
            setLocalError('Please enter success criteria')
            return
        }

        const numAmount = parseInt(amount)
        if (!amount || isNaN(numAmount) || numAmount <= 0) {
            setLocalError('Please enter a valid stake amount')
            return
        }

        if (user && numAmount > user.points) {
            setLocalError(`You only have ${user.points} points`)
            return
        }

        onSubmit(title.trim(), criteria.trim(), numAmount)
    }

    const handleBackdropClick = (e: MouseEvent<HTMLDivElement>) => {
        if (e.target === e.currentTarget) {
            onClose()
        }
    }

    if (!isAuthenticated) {
        return null
    }

    const renderError = () => {
        const displayError = localError || error
        if (!displayError) return null

        if (typeof displayError === 'object') {
            return displayError.detail?.[0]?.msg || displayError.message || JSON.stringify(displayError)
        }
        return displayError
    }

    return (
        <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={handleBackdropClick}
        >
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 transform transition-all">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-3xl font-bold bg-gradient-to-r from-competitive-dark to-friendly-dark bg-clip-text text-transparent">
                        Create a Bet
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 transition-colors text-3xl font-light leading-none"
                        aria-label="Close"
                    >
                        ×
                    </button>
                </div>

                <p className="text-gray-600 mb-6">
                    Stake your points on a commitment. If you complete it, you win challenger stakes!
                </p>

                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <label htmlFor="title" className="block text-sm font-semibold text-gray-700 mb-2">
                            What's your commitment?
                        </label>
                        <input
                            type="text"
                            id="title"
                            value={title}
                            onChange={(e) => {
                                setTitle(e.target.value)
                                setLocalError('')
                                onClearError?.()
                            }}
                            placeholder="e.g., Run 5km every day for a week"
                            className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-competitive-DEFAULT focus:ring-2 focus:ring-competitive-light text-lg"
                            autoFocus
                        />
                    </div>

                    <div className="mb-4">
                        <label htmlFor="criteria" className="block text-sm font-semibold text-gray-700 mb-2">
                            Success Criteria
                        </label>
                        <textarea
                            id="criteria"
                            value={criteria}
                            onChange={(e) => {
                                setCriteria(e.target.value)
                                setLocalError('')
                                onClearError?.()
                            }}
                            placeholder="How will you prove success? e.g., Screenshot from fitness app"
                            rows={2}
                            className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-competitive-DEFAULT focus:ring-2 focus:ring-competitive-light"
                        />
                    </div>

                    <div className="mb-6">
                        <label htmlFor="amount" className="block text-sm font-semibold text-gray-700 mb-2">
                            Your Stake (Points)
                        </label>
                        <input
                            type="number"
                            id="amount"
                            value={amount}
                            onChange={(e) => {
                                setAmount(e.target.value)
                                setLocalError('')
                                onClearError?.()
                            }}
                            min="1"
                            placeholder="Enter amount to stake"
                            className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-competitive-DEFAULT focus:ring-2 focus:ring-competitive-light text-lg"
                        />
                        {user && (
                            <p className="text-xs text-gray-500 mt-1">Available: {user.points} points</p>
                        )}
                    </div>

                    {(localError || error) && (
                        <p className="mb-4 text-sm text-red-600">{renderError()}</p>
                    )}

                    <div className="flex gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="flex-1 px-6 py-3 bg-gradient-to-r from-competitive-dark to-competitive-DEFAULT text-white rounded-lg font-semibold hover:from-competitive-DEFAULT hover:to-competitive-light transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
                        >
                            Create Bet
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}