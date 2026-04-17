import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { X, Plug, Mail, HardDrive, FileSpreadsheet, Calendar, Youtube, CheckCircle2, XCircle, Link2 } from 'lucide-react';
import { toast } from 'sonner';

export default function IntegrationsPanel({ onClose }) {
  const { api } = useAuth();
  const [googleStatus, setGoogleStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/integrations/google/status');
      setGoogleStatus(data);
    } catch (e) { console.error(e); }
  }, [api]);

  useEffect(() => { load(); }, [load]);

  const connectGoogle = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/integrations/google/start');
      // Redireciona a janela principal para autorização do Google
      window.location.href = data.auth_url;
    } catch (e) {
      const detail = e.response?.data?.detail || 'Erro ao iniciar fluxo OAuth';
      toast.error(detail);
      setLoading(false);
    }
  };

  const disconnectGoogle = async () => {
    if (!window.confirm('Desconectar sua conta Google? Isso revoga os tokens.')) return;
    try {
      await api.post('/integrations/google/disconnect');
      toast.success('Conta Google desconectada');
      load();
    } catch (e) { toast.error('Erro ao desconectar'); }
  };

  const SERVICE_ICONS = [
    { Icon: Mail, label: 'Gmail' },
    { Icon: HardDrive, label: 'Drive' },
    { Icon: FileSpreadsheet, label: 'Sheets' },
    { Icon: Calendar, label: 'Calendar' },
    { Icon: Youtube, label: 'YouTube' },
  ];

  return (
    <div data-testid="integrations-panel" className="fixed inset-0 z-50 flex items-center justify-center p-3" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}>
      <div className="w-full max-w-2xl max-h-[92vh] overflow-hidden flex flex-col" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        <div className="flex items-center justify-between px-5 py-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
              <Plug className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
            </div>
            <h2 className="text-sm font-bold tracking-wider uppercase" style={{ fontFamily: 'Outfit, sans-serif' }}>Minhas Integrações</h2>
          </div>
          <button data-testid="integrations-close-btn" onClick={onClose} className="p-1.5" style={{ color: 'var(--text-tertiary)' }}>
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4" style={{ background: 'var(--bg-base)' }}>
          {!googleStatus ? (
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Carregando...</p>
          ) : (
            <div data-testid="google-integration-card" className="p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(234,67,53,0.1)' }}>
                    {/* Google "G" emblem simples */}
                    <span className="text-lg font-bold" style={{ color: '#EA4335' }}>G</span>
                  </div>
                  <div>
                    <h3 className="text-sm font-bold" style={{ fontFamily: 'Outfit, sans-serif' }}>Google Workspace</h3>
                    <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Gmail · Drive · Sheets · Calendar · YouTube</p>
                  </div>
                </div>
                {googleStatus.connected ? (
                  <span className="flex items-center gap-1 px-2 py-1 text-[10px] font-bold uppercase tracking-wider" style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--success)' }}>
                    <CheckCircle2 className="w-3 h-3" /> Conectado
                  </span>
                ) : googleStatus.integration_available ? (
                  <span className="flex items-center gap-1 px-2 py-1 text-[10px] font-bold uppercase tracking-wider" style={{ background: 'var(--bg-base)', color: 'var(--text-tertiary)' }}>
                    <XCircle className="w-3 h-3" /> Desconectado
                  </span>
                ) : (
                  <span className="flex items-center gap-1 px-2 py-1 text-[10px] font-bold uppercase tracking-wider" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--error)' }}>
                    Não configurado pelo admin
                  </span>
                )}
              </div>

              {/* Serviços cobertos */}
              <div className="flex items-center gap-3 mb-4 py-3 px-3" style={{ background: 'var(--bg-base)' }}>
                {SERVICE_ICONS.map(({ Icon, label }) => (
                  <div key={label} className="flex flex-col items-center gap-1 flex-1">
                    <Icon className="w-4 h-4" style={{ color: googleStatus.connected ? 'var(--accent)' : 'var(--text-tertiary)' }} />
                    <span className="text-[10px] tracking-wider uppercase" style={{ color: 'var(--text-tertiary)' }}>{label}</span>
                  </div>
                ))}
              </div>

              {googleStatus.connected && googleStatus.account && (
                <div className="mb-4 p-3 flex items-center gap-3" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}>
                  {googleStatus.account.google_picture && (
                    <img src={googleStatus.account.google_picture} alt="" className="w-9 h-9 rounded-full" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{googleStatus.account.google_name || '—'}</p>
                    <p className="text-[11px] truncate" style={{ color: 'var(--text-tertiary)' }}>{googleStatus.account.google_email}</p>
                  </div>
                  <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                    desde {new Date(googleStatus.account.connected_at).toLocaleDateString('pt-BR')}
                  </span>
                </div>
              )}

              {googleStatus.connected ? (
                <button
                  data-testid="disconnect-google-btn"
                  onClick={disconnectGoogle}
                  className="w-full py-2.5 px-4 text-xs font-bold flex items-center justify-center gap-2 transition-colors"
                  style={{ background: 'var(--bg-elevated)', color: 'var(--error)', border: '1px solid rgba(239,68,68,0.3)' }}
                >
                  <XCircle className="w-3.5 h-3.5" /> Desconectar
                </button>
              ) : (
                <button
                  data-testid="connect-google-btn"
                  onClick={connectGoogle}
                  disabled={!googleStatus.integration_available || loading}
                  className="w-full py-2.5 px-4 text-xs font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}
                >
                  <Link2 className="w-3.5 h-3.5" />
                  {loading ? 'Abrindo Google...' : 'Conectar minha conta Google'}
                </button>
              )}

              {!googleStatus.integration_available && (
                <p className="mt-3 text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
                  O administrador precisa configurar Client ID e Secret do Google no Painel Admin → Integrações antes de você poder conectar.
                </p>
              )}
            </div>
          )}

          {/* Futuras integrações — placeholder visual */}
          <div className="p-4 opacity-50" style={{ background: 'var(--bg-surface)', border: '1px dashed var(--border-subtle)' }}>
            <p className="text-xs font-bold mb-1" style={{ fontFamily: 'Outfit, sans-serif' }}>Próximas integrações</p>
            <p className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>Meta (Instagram/WhatsApp), TikTok, Dropbox — em breve</p>
          </div>
        </div>
      </div>
    </div>
  );
}
