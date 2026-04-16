import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { MessageCircle, Link, Unlink, ExternalLink, Check, AlertCircle, Copy } from 'lucide-react';

export default function TelegramIntegration() {
  const { api } = useAuth();
  const [status, setStatus] = useState(null);
  const [token, setToken] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/telegram/status');
        setStatus(data);
      } catch (e) { console.error(e); }
    })();
  }, [api]);

  const connect = async () => {
    if (!token.trim()) return;
    setConnecting(true);
    setError('');
    setSuccess('');
    try {
      const { data } = await api.post('/telegram/connect', { bot_token: token.trim() });
      setSuccess(data.message);
      setToken('');
      const { data: st } = await api.get('/telegram/status');
      setStatus(st);
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao conectar');
    }
    setConnecting(false);
  };

  const disconnect = async () => {
    try {
      await api.post('/telegram/disconnect');
      setStatus({ connected: false, connection: null });
      setSuccess('Bot desconectado');
      setTimeout(() => setSuccess(''), 3000);
    } catch (e) {
      setError('Erro ao desconectar');
    }
  };

  const copyBotLink = () => {
    if (status?.connection?.bot_username) {
      navigator.clipboard.writeText(`https://t.me/${status.connection.bot_username}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2 mb-2">
        <MessageCircle className="w-4 h-4" style={{ color: '#0088cc' }} />
        <h3 className="text-sm font-semibold" style={{ fontFamily: 'Outfit, sans-serif' }}>Integracao Telegram</h3>
      </div>

      {/* Connected state */}
      {status?.connected && status.connection && (
        <div className="animate-fade-in">
          <div className="p-4 flex items-start gap-3" style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.3)' }}>
            <Check className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: 'var(--success)' }} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium" style={{ color: 'var(--success)' }}>Bot Conectado</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                @{status.connection.bot_username} ({status.connection.bot_name})
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
                Conectado em {new Date(status.connection.connected_at).toLocaleDateString('pt-BR')}
              </p>
            </div>
          </div>

          {/* Bot link */}
          <div className="mt-3 p-3 flex items-center gap-2" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
            <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" style={{ color: '#0088cc' }} />
            <a
              href={`https://t.me/${status.connection.bot_username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 text-xs font-mono truncate"
              style={{ color: '#0088cc' }}
            >
              t.me/{status.connection.bot_username}
            </a>
            <button
              data-testid="copy-bot-link"
              onClick={copyBotLink}
              className="p-1.5 transition-colors"
              style={{ color: copied ? 'var(--success)' : 'var(--text-tertiary)' }}
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>

          <p className="text-xs mt-3" style={{ color: 'var(--text-secondary)' }}>
            Abra o Telegram, busque por <strong>@{status.connection.bot_username}</strong> e mande uma mensagem. O Mordomo Virtual vai responder!
          </p>

          <button
            data-testid="disconnect-telegram-btn"
            onClick={disconnect}
            className="mt-4 w-full py-2.5 text-sm font-medium flex items-center justify-center gap-2 transition-colors"
            style={{ border: '1px solid rgba(239,68,68,0.3)', color: 'var(--error)', background: 'rgba(239,68,68,0.05)' }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.15)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(239,68,68,0.05)'}
          >
            <Unlink className="w-4 h-4" /> Desconectar Bot
          </button>
        </div>
      )}

      {/* Not connected state */}
      {(!status?.connected) && (
        <div className="animate-fade-in">
          {/* Instructions */}
          <div className="p-3 mb-4" style={{ background: 'var(--terminal-bg)', border: '1px solid var(--border-subtle)' }}>
            <p className="text-xs font-mono mb-2" style={{ color: 'var(--accent)' }}>Como criar seu bot:</p>
            <ol className="text-xs font-mono flex flex-col gap-1" style={{ color: 'var(--terminal-text)' }}>
              <li>1. Abra o Telegram e busque @BotFather</li>
              <li>2. Envie /newbot e siga as instrucoes</li>
              <li>3. Copie o token do bot</li>
              <li>4. Cole o token aqui embaixo</li>
            </ol>
          </div>

          {error && (
            <div className="mb-3 p-3 flex items-center gap-2" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
              <AlertCircle className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--error)' }} />
              <p className="text-xs" style={{ color: 'var(--error)' }}>{error}</p>
            </div>
          )}

          {success && (
            <div className="mb-3 p-3 flex items-center gap-2" style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)' }}>
              <Check className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--success)' }} />
              <p className="text-xs" style={{ color: 'var(--success)' }}>{success}</p>
            </div>
          )}

          <div className="flex flex-col gap-3">
            <div>
              <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>Token do Bot (@BotFather)</label>
              <input
                data-testid="telegram-token-input"
                value={token}
                onChange={e => setToken(e.target.value)}
                className="w-full py-2.5 px-3 text-sm outline-none font-mono"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                placeholder="123456789:ABCdefGHI..."
                type="password"
              />
            </div>
            <button
              data-testid="connect-telegram-btn"
              onClick={connect}
              disabled={connecting || !token.trim()}
              className="w-full py-2.5 text-sm font-medium flex items-center justify-center gap-2 transition-colors"
              style={{
                background: connecting ? 'var(--accent-hover)' : '#0088cc',
                color: 'white',
                opacity: !token.trim() ? 0.5 : 1,
              }}
            >
              <Link className="w-4 h-4" />
              {connecting ? 'Conectando...' : 'Conectar Bot do Telegram'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
