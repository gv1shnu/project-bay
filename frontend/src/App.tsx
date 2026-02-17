/**
 * App.tsx — Root component and route definitions.
 *
 * Wraps everything in AuthProvider (global auth state),
 * then defines routes using React Router.
 *
 * All routes are public — auth is enforced per-action
 * (e.g., creating a bet requires login), not per-page.
 */
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import HomePage from './pages/HomePage';
import ProfilePage from './pages/ProfilePage';
import AdminPage from './pages/AdminPage';
import NotificationsPage from './pages/NotificationsPage';

function App() {
  return (
    // AuthProvider makes user state available to all child components
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public auth pages */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          {/* Profile page — accepts username as URL param */}
          <Route path="/profile/:username" element={<ProfilePage />} />

          {/* Main feed — shows all public bets */}
          <Route path="/" element={<HomePage />} />

          {/* Notifications — user's activity feed */}
          <Route path="/notifications" element={<NotificationsPage />} />

          {/* Admin dashboard — view all users and bets */}
          <Route path="/admin" element={<AdminPage />} />

          {/* Catch-all — redirect unknown paths to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
