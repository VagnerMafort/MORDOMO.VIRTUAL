import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { Eye, EyeOff, Sun, Moon } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export default function LoginPage() {
  const { login, register } = useAuth();
  const { theme, toggle: toggleTheme } = useTheme();
  const [isRegister, setIsRegister] = useState(false);
  const [isForgot, setIsForgot] = useState(false);
  const [resetMode, setResetMode] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
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
    setError(''); setInfo('');
    setLoading(true);
    try {
      if (isForgot && !resetMode) {
        await axios.post(`${API}/auth/forgot-password`, { email });
        setInfo('Se o e-mail estiver cadastrado, um token foi gerado. Solicite ao administrador.');
      } else if (resetMode) {
        await axios.post(`${API}/auth/reset-password`, { token: resetToken, new_password: password });
        setInfo('Senha redefinida com sucesso! Entre com sua nova senha.');
        setResetMode(false); setIsForgot(false);
        setResetToken(''); setPassword('');
      } else if (isRegister) {
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
      <button
        data-testid="theme-toggle-btn"
        onClick={toggleTheme}
        title={theme === 'dark' ? 'Tema claro' : 'Tema escuro'}
        className="absolute top-4 right-4 z-20 p-2 transition-colors"
        style={{ background: 'var(--bg-surface)', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}
      >
        {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      </button>
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `url(https://images.unsplash.com/photo-1775057154553-0f3e8902fea3?w=1920&q=60)`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />
      <div className="absolute inset-0" style={{ background: theme === 'dark' ? 'rgba(10,10,10,0.85)' : 'rgba(255,255,255,0.85)' }} />

      <div
        data-testid="auth-form-container"
        className="relative z-10 w-full max-w-md animate-fade-in"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}
      >
        <div className="p-8">
          <div className="flex items-center gap-3 mb-8">
            <img src="/kaelum-icon.png" alt="Kaelum.AI" className="w-12 h-12 object-contain flex-shrink-0" />
            <div>
              <h1 className="text-2xl font-black tracking-tighter" style={{ fontFamily: 'Outfit, sans-serif', color: 'var(--text-primary)' }}>
                Kaelum<span style={{ color: 'var(--accent-soft)' }}>.AI</span>
              </h1>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                Assistente Virtual Inteligente
              </p>
            </div>
          </div>

          <h2 className="text-lg font-semibold mb-6" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {resetMode ? 'Redefinir Senha' : isForgot ? 'Esqueci minha senha' : isRegister ? 'Criar Conta' : 'Entrar no Sistema'}
          </h2>

          {error && (
            <div data-testid="auth-error" className="mb-4 p-3 text-sm" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: 'var(--error)' }}>
              {error}
            </div>
          )}
          {info && (
            <div data-testid="auth-info" className="mb-4 p-3 text-sm" style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', color: 'var(--success)' }}>
              {info}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {isRegister && !isForgot && !resetMode && (
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
            {!resetMode && (
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
            )}
            {resetMode && (
              <div>
                <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>Token de recuperação</label>
                <input
                  data-testid="reset-token-input"
                  type="text"
                  value={resetToken}
                  onChange={e => setResetToken(e.target.value)}
                  required
                  placeholder="Cole aqui o token recebido"
                  className="w-full py-3 px-4 text-sm outline-none transition-all"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                />
              </div>
            )}
            {!isForgot && (
              <div>
                <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>
                  {resetMode ? 'Nova senha' : 'Senha'}
                </label>
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
            )}

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
                resetMode ? 'Redefinir senha' : isForgot ? 'Gerar token de recuperação' : isRegister ? 'Criar Conta' : 'Entrar'
              )}
            </button>
          </form>

          <div className="mt-6 text-center flex flex-col gap-2">
            <button
              data-testid="toggle-auth-mode"
              onClick={() => { setIsRegister(!isRegister); setIsForgot(false); setResetMode(false); setError(''); setInfo(''); }}
              className="text-sm transition-colors"
              style={{ color: 'var(--text-tertiary)' }}
              onMouseEnter={e => e.target.style.color = 'var(--accent)'}
              onMouseLeave={e => e.target.style.color = 'var(--text-tertiary)'}
            >
              {isRegister ? 'Ja tem conta? Entrar' : 'Nao tem conta? Criar'}
            </button>
            {!isRegister && !resetMode && (
              <button
                data-testid="forgot-password-btn"
                onClick={() => { setIsForgot(!isForgot); setError(''); setInfo(''); }}
                className="text-xs transition-colors"
                style={{ color: 'var(--text-tertiary)' }}
              >
                {isForgot ? '← Voltar ao login' : 'Esqueci minha senha'}
              </button>
            )}
            {!isRegister && (
              <button
                data-testid="have-token-btn"
                onClick={() => { setResetMode(!resetMode); setIsForgot(false); setError(''); setInfo(''); }}
                className="text-xs transition-colors"
                style={{ color: 'var(--text-tertiary)' }}
              >
                {resetMode ? '← Voltar ao login' : 'Já tenho um token de recuperação'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
