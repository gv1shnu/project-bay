/**
 * ProtectedRoute.tsx — Route guard for authenticated-only pages.
 *
 * Wraps a page component and redirects to /login if the user isn't logged in.
 * Shows a loading state while the initial auth check is in progress.
 *
 * NOTE: Currently unused — all pages are public, and auth is enforced per-action.
 * Kept for future use if any routes need full-page authentication.
 *
 * Usage:
 *   <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
 */
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;  // The page component to protect
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, loading } = useAuth();

  // Still checking stored token — don't redirect yet
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading...</p>
      </div>
    );
  }

  // Not authenticated — redirect to login page
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Authenticated — render the protected content
  return <>{children}</>;
}
