/**
 * AuthPrompt.tsx — Sign-in/sign-up prompt modal.
 *
 * Displayed when an unauthenticated user tries to perform an action
 * that requires login (e.g., creating a bet or challenging someone).
 * Offers navigation to login or signup pages.
 */
import { useNavigate } from 'react-router-dom';

interface AuthPromptProps {
  onClose: () => void;        // Callback to close the modal
  message?: string;           // Optional custom prompt message
}

export default function AuthPrompt({ onClose, message }: AuthPromptProps) {
  const navigate = useNavigate();

  return (
    // Full-screen backdrop — clicking it closes the modal
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      {/* Modal card — stop propagation so clicking inside doesn't close it */}
      <div
        className="bg-white rounded-2xl shadow-xl max-w-md w-full p-8 text-center"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Bay logo/icon */}
        <div className="flex justify-center mb-6">
          <div className="bg-competitive-100 rounded-full p-4">
            <svg className="w-8 h-8 text-competitive-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        </div>

        {/* Prompt message */}
        <h2 className="text-2xl font-bold text-gray-900 mb-3">Join the Bay</h2>
        <p className="text-gray-600 mb-8 text-lg">
          {message || 'Sign in to create bets, challenge others, and start competing!'}
        </p>

        {/* Action buttons — navigate to auth pages */}
        <div className="space-y-3">
          <button
            onClick={() => navigate('/login')}
            className="w-full py-3 bg-competitive-500 text-white rounded-xl font-semibold hover:bg-competitive-600 transition-colors"
          >
            Sign In
          </button>
          <button
            onClick={() => navigate('/signup')}
            className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl font-semibold hover:bg-gray-200 transition-colors"
          >
            Create Account
          </button>
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="mt-6 text-gray-400 hover:text-gray-600 text-sm transition-colors"
        >
          Maybe later
        </button>
      </div>
    </div>
  );
}
