import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Eye, EyeOff, Zap } from 'lucide-react';

export default function LoginPage() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const formatError = (detail) => {
    if (!detail) return 'Algo deu errado. Tente novamente.';
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map(e => e?.msg || JSON.stringify(e)).join(' ');
    if (detail?.msg) return detail.msg;
    return String(detail);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isRegister) {
        await register(email, password, name);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(formatError(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'var(--bg-base)' }}>
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `url(https://images.unsplash.com/photo-1775057154553-0f3e8902fea3?w=1920&q=60)`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />
      <div className="absolute inset-0" style={{ background: 'rgba(10,10,10,0.85)' }} />

      <div
        data-testid="auth-form-container"
        className="relative z-10 w-full max-w-md animate-fade-in"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}
      >
        <div className="p-8">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
              <Zap className="w-5 h-5" style={{ color: 'var(--accent-text)' }} />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tighter" style={{ fontFamily: 'Outfit, sans-serif' }}>
                Mordomo Virtual
              </h1>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                Mordomo Virtual AI
              </p>
            </div>
          </div>

          <h2 className="text-lg font-semibold mb-6" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {isRegister ? 'Criar Conta' : 'Entrar no Sistema'}
          </h2>

          {error && (
            <div data-testid="auth-error" className="mb-4 p-3 text-sm" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: 'var(--error)' }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {isRegister && (
              <div>
                <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>Nome</label>
                <input
                  data-testid="register-name-input"
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  required
                  placeholder="Seu nome"
                  className="w-full py-3 px-4 text-sm outline-none transition-all"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                  onFocus={e => e.target.style.borderColor = 'var(--accent)'}
                  onBlur={e => e.target.style.borderColor = 'var(--border-subtle)'}
                />
              </div>
            )}
            <div>
              <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>E-mail de Acesso</label>
              <input
                data-testid="login-email-input"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                placeholder="seu@email.com"
                className="w-full py-3 px-4 text-sm outline-none transition-all"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                onFocus={e => e.target.style.borderColor = 'var(--accent)'}
                onBlur={e => e.target.style.borderColor = 'var(--border-subtle)'}
              />
            </div>
            <div>
              <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>Senha</label>
              <div className="relative">
                <input
                  data-testid="login-password-input"
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  placeholder="********"
                  className="w-full py-3 px-4 pr-12 text-sm outline-none transition-all"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                  onFocus={e => e.target.style.borderColor = 'var(--accent)'}
                  onBlur={e => e.target.style.borderColor = 'var(--border-subtle)'}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text-tertiary)' }}
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              data-testid="auth-submit-btn"
              type="submit"
              disabled={loading}
              className="w-full py-3 px-6 text-sm font-semibold transition-colors flex items-center justify-center gap-2"
              style={{
                background: loading ? 'var(--accent-hover)' : 'var(--accent)',
                color: 'var(--accent-text)',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? (
                <span className="typing-indicator flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--accent-text)' }} />
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--accent-text)' }} />
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--accent-text)' }} />
                </span>
              ) : (
                isRegister ? 'Criar Conta' : 'Entrar'
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              data-testid="toggle-auth-mode"
              onClick={() => { setIsRegister(!isRegister); setError(''); }}
              className="text-sm transition-colors"
              style={{ color: 'var(--text-tertiary)' }}
              onMouseEnter={e => e.target.style.color = 'var(--accent)'}
              onMouseLeave={e => e.target.style.color = 'var(--text-tertiary)'}
            >
              {isRegister ? 'Ja tem conta? Entrar' : 'Nao tem conta? Criar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
