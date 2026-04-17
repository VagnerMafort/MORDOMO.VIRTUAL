import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { ThemeProvider, useTheme } from "@/contexts/ThemeContext";
import { Toaster } from "sonner";
import LoginPage from "@/pages/LoginPage";
import ChatPage from "@/pages/ChatPage";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ background: 'var(--bg-base)' }}>
        <div className="text-center animate-fade-in">
          <div className="w-12 h-12 mx-auto mb-4 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
            <svg className="w-6 h-6 animate-spin" style={{ color: 'var(--accent-text)' }} fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Carregando...</p>
        </div>
      </div>
    );
  }
  if (user === false) return <Navigate to="/login" replace />;
  return children;
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/" replace />;
  return children;
}

function AppContent() {
  return (
    <BrowserRouter>
      <ThemedToaster />
      <Routes>
        <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
        <Route path="/*" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
}

function ThemedToaster() {
  const { theme } = useTheme();
  return <Toaster position="top-right" theme={theme} />;
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
