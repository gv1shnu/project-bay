/**
 * ProofUploadModal.tsx — Modal for uploading proof of bet completion.
 *
 * Shown when a bet is "active" and the current user is the bet creator.
 * Features:
 *   - Countdown timer showing remaining time until bet deadline
 *   - Text area for comments explaining the proof
 *   - File picker for image/video evidence
 *   - Preview of selected media before upload
 */
import { useState, useEffect, FormEvent, MouseEvent, useRef } from 'react'

interface ProofUploadModalProps {
    betTitle: string
    proofDeadline: string   // ISO date string — bet deadline (proof must be uploaded before this)
    onClose: () => void
    onSubmit: (comment: string, file: File) => Promise<void>
}

export default function ProofUploadModal({ betTitle, proofDeadline, onClose, onSubmit }: ProofUploadModalProps) {
    const [comment, setComment] = useState('')
    const [file, setFile] = useState<File | null>(null)
    const [preview, setPreview] = useState<string | null>(null)
    const [uploading, setUploading] = useState(false)
    const [error, setError] = useState('')
    const [timeLeft, setTimeLeft] = useState('')
    const fileInputRef = useRef<HTMLInputElement>(null)

    // Lock body scroll while modal is open
    useEffect(() => {
        document.body.style.overflow = 'hidden'
        return () => { document.body.style.overflow = 'unset' }
    }, [])

    // Countdown timer — updates every second
    useEffect(() => {
        const update = () => {
            const now = Date.now()
            // Backend sends UTC datetimes — ensure the string is parsed as UTC
            // If no timezone indicator, append 'Z' so JS treats it as UTC
            const deadlineStr = proofDeadline.endsWith('Z') || proofDeadline.includes('+')
                ? proofDeadline
                : proofDeadline + 'Z'
            const deadline = new Date(deadlineStr).getTime()
            const diff = deadline - now

            if (diff <= 0) {
                setTimeLeft('Expired')
                return
            }

            const hours = Math.floor(diff / 3600000)
            const mins = Math.floor((diff % 3600000) / 60000)
            const secs = Math.floor((diff % 60000) / 1000)
            setTimeLeft(hours > 0 ? `${hours}h ${mins}m ${secs}s` : `${mins}m ${secs}s`)
        }

        update()
        const interval = setInterval(update, 1000)
        return () => clearInterval(interval)
    }, [proofDeadline])

    /** Generate a preview URL when a file is selected */
    useEffect(() => {
        if (!file) {
            setPreview(null)
            return
        }
        const url = URL.createObjectURL(file)
        setPreview(url)
        return () => URL.revokeObjectURL(url)
    }, [file])

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0]
        if (!selected) return

        // 10 MB limit
        if (selected.size > 10 * 1024 * 1024) {
            setError('File too large (max 10 MB)')
            return
        }

        setFile(selected)
        setError('')
    }

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError('')

        if (!comment.trim()) {
            setError('Please add a comment describing your proof')
            return
        }

        if (!file) {
            setError('Please select a file to upload')
            return
        }

        if (timeLeft === 'Expired') {
            setError('Deadline has passed — proof can no longer be uploaded')
            return
        }

        setUploading(true)
        try {
            await onSubmit(comment.trim(), file)
        } catch (err: any) {
            setError(err.message || 'Upload failed')
        }
        setUploading(false)
    }

    const handleBackdropClick = (e: MouseEvent<HTMLDivElement>) => {
        if (e.target === e.currentTarget && !uploading) {
            onClose()
        }
    }

    const isVideo = file?.type.startsWith('video/')

    return (
        <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={handleBackdropClick}
        >
            <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-8 transform transition-all max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h2 className="text-2xl font-bold bg-gradient-to-r from-yellow-600 to-orange-500 bg-clip-text text-transparent">
                            Upload Proof
                        </h2>
                        <p className="text-sm text-gray-500 mt-1 line-clamp-1">{betTitle}</p>
                    </div>
                    <button
                        onClick={onClose}
                        disabled={uploading}
                        className="text-gray-400 hover:text-gray-600 transition-colors text-3xl font-light leading-none"
                        aria-label="Close"
                    >
                        ×
                    </button>
                </div>

                {/* Countdown timer */}
                <div className={`flex items-center gap-2 mb-6 px-4 py-3 rounded-lg ${timeLeft === 'Expired' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
                    }`}>
                    <span className="text-lg">⏱️</span>
                    <span className="font-semibold">
                        {timeLeft === 'Expired' ? 'Deadline has passed' : `Time remaining: ${timeLeft}`}
                    </span>
                </div>

                <form onSubmit={handleSubmit}>
                    {/* Comment field */}
                    <div className="mb-4">
                        <label htmlFor="proof-comment" className="block text-sm font-semibold text-gray-700 mb-2">
                            Describe your proof
                        </label>
                        <textarea
                            id="proof-comment"
                            value={comment}
                            onChange={(e) => { setComment(e.target.value); setError('') }}
                            placeholder="Explain how you completed your commitment..."
                            rows={3}
                            maxLength={1000}
                            className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-200"
                            autoFocus
                        />
                        <p className="text-xs text-gray-400 mt-1 text-right">{comment.length}/1000</p>
                    </div>

                    {/* File picker */}
                    <div className="mb-4">
                        <label className="block text-sm font-semibold text-gray-700 mb-2">
                            Upload evidence
                        </label>
                        <div
                            className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-amber-400 hover:bg-amber-50/30 transition-colors"
                            onClick={() => fileInputRef.current?.click()}
                        >
                            {preview ? (
                                <div className="space-y-2">
                                    {isVideo ? (
                                        <video src={preview} className="max-h-48 mx-auto rounded-lg" controls />
                                    ) : (
                                        <img src={preview} alt="Preview" className="max-h-48 mx-auto rounded-lg object-contain" />
                                    )}
                                    <p className="text-sm text-gray-500">{file?.name}</p>
                                    <button
                                        type="button"
                                        className="text-sm text-red-500 hover:text-red-700"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            setFile(null)
                                            if (fileInputRef.current) fileInputRef.current.value = ''
                                        }}
                                    >
                                        Remove
                                    </button>
                                </div>
                            ) : (
                                <div>
                                    <p className="text-4xl mb-2">📎</p>
                                    <p className="text-gray-600 font-medium">Click to select a file</p>
                                    <p className="text-xs text-gray-400 mt-1">Images or videos, max 10 MB</p>
                                </div>
                            )}
                        </div>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*,video/*"
                            onChange={handleFileChange}
                            className="hidden"
                        />
                    </div>

                    {/* Error display */}
                    {error && (
                        <p className="mb-4 text-sm text-red-600">{error}</p>
                    )}

                    {/* Action buttons */}
                    <div className="flex gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            disabled={uploading}
                            className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors disabled:opacity-50"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={uploading || timeLeft === 'Expired'}
                            className="flex-1 px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg font-semibold hover:from-amber-600 hover:to-orange-600 transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5 disabled:opacity-50 disabled:transform-none"
                        >
                            {uploading ? 'Uploading...' : 'Submit Proof'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}
