import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { X, Share2, Upload, CheckCircle2, XCircle, Clock, Eye, EyeOff, Globe } from 'lucide-react';
import { toast } from 'sonner';

export default function SocialPublisher({ onClose }) {
  const { api } = useAuth();
  const [networks, setNetworks] = useState([]);
  const [selected, setSelected] = useState([]);
  const [form, setForm] = useState({ title: '', description: '', tags: '', privacy: 'private' });
  const [file, setFile] = useState(null);
  const [publishing, setPublishing] = useState(false);
  const [results, setResults] = useState(null);

  const load = useCallback(async () => {
    try { const { data } = await api.get('/social/networks'); setNetworks(data.networks || []); } catch {}
  }, [api]);
  useEffect(() => { load(); }, [load]);

  const toggle = (key) => setSelected(s => s.includes(key) ? s.filter(k => k !== key) : [...s, key]);

  const submit = async () => {
    if (!file) { toast.error('Selecione um arquivo de vídeo'); return; }
    if (!form.title) { toast.error('Título é obrigatório'); return; }
    if (selected.length === 0) { toast.error('Selecione ao menos uma rede'); return; }
    setPublishing(true); setResults(null);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('title', form.title);
    fd.append('description', form.description);
    fd.append('tags', form.tags);
    fd.append('privacy', form.privacy);
    fd.append('networks', selected.join(','));
    try {
      const { data } = await api.post('/social/publish', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setResults(data.results);
      toast.success(data.summary);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao publicar');
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div data-testid="social-publisher" className="fixed inset-0 z-50 flex items-center justify-center p-3" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}>
      <div className="w-full max-w-2xl max-h-[92vh] overflow-hidden flex flex-col" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        <div className="flex items-center justify-between px-5 py-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
              <Share2 className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
            </div>
            <h2 className="text-sm font-bold tracking-wider uppercase" style={{ fontFamily: 'Outfit, sans-serif' }}>Publicar em Redes Sociais</h2>
          </div>
          <button data-testid="social-close-btn" onClick={onClose} style={{ color: 'var(--text-tertiary)' }}><X className="w-4 h-4" /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4" style={{ background: 'var(--bg-base)' }}>
          {/* Networks */}
          <div>
            <label className="text-[10px] uppercase tracking-wider block mb-2" style={{ color: 'var(--text-tertiary)' }}>Redes</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {networks.map(n => {
                const isSel = selected.includes(n.key);
                const disabled = !n.available || !n.connected;
                return (
                  <button key={n.key} data-testid={`network-${n.key}`}
                    onClick={() => !disabled && toggle(n.key)} disabled={disabled}
                    className="p-3 text-left transition-all flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                      background: isSel ? 'var(--accent)' : 'var(--bg-surface)',
                      border: `1px solid ${isSel ? 'var(--accent)' : 'var(--border-subtle)'}`,
                      color: isSel ? 'var(--accent-text)' : 'var(--text-primary)',
                    }}>
                    <Globe className="w-4 h-4 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold">{n.name}</p>
                      <p className="text-[10px] opacity-70">{n.connected ? 'Conectado' : (n.message || 'Desconectado')}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* File */}
          <div>
            <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>Arquivo de mídia</label>
            <label className="flex items-center gap-2 p-3 cursor-pointer transition-colors" style={{ background: 'var(--bg-surface)', border: '1px dashed var(--border-subtle)' }}>
              <Upload className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
              <span className="text-xs flex-1" style={{ color: file ? 'var(--text-primary)' : 'var(--text-tertiary)' }}>{file ? file.name : 'Clique para selecionar vídeo'}</span>
              {file && <span className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>{(file.size / 1024 / 1024).toFixed(1)} MB</span>}
              <input data-testid="social-file-input" type="file" accept="video/*,image/*" className="hidden" onChange={e => setFile(e.target.files?.[0])} />
            </label>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>Título</label>
              <input data-testid="social-title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
                className="w-full px-2 py-1.5 text-xs" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>Privacidade</label>
              <select data-testid="social-privacy" value={form.privacy} onChange={e => setForm({ ...form, privacy: e.target.value })}
                className="w-full px-2 py-1.5 text-xs" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
                <option value="private">Privado</option>
                <option value="unlisted">Não listado</option>
                <option value="public">Público</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>Descrição</label>
            <textarea data-testid="social-description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
              rows={4} className="w-full px-2 py-1.5 text-xs" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
          </div>

          <div>
            <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>Tags (separadas por vírgula)</label>
            <input data-testid="social-tags" value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })}
              placeholder="ia, mordomo, automacao"
              className="w-full px-2 py-1.5 text-xs" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
          </div>

          {results && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-bold tracking-wider uppercase" style={{ color: 'var(--text-secondary)' }}>Resultados</h4>
              {results.map((r, i) => {
                const Icon = r.status === 'ok' ? CheckCircle2 : r.status === 'not_implemented' ? Clock : XCircle;
                const color = r.status === 'ok' ? 'var(--success)' : r.status === 'not_implemented' ? 'var(--text-tertiary)' : 'var(--error)';
                return (
                  <div key={i} className="p-3 flex items-center gap-3 text-xs" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                    <Icon className="w-4 h-4" style={{ color }} />
                    <span className="font-bold" style={{ color: 'var(--text-primary)' }}>{r.network}</span>
                    {r.url && <a href={r.url} target="_blank" rel="noreferrer" className="flex-1 truncate" style={{ color: 'var(--accent)' }}>{r.url}</a>}
                    {r.message && <span className="flex-1 truncate" style={{ color }}>{r.message}</span>}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="px-5 py-3 border-t" style={{ borderColor: 'var(--border-subtle)' }}>
          <button data-testid="social-publish-btn" onClick={submit} disabled={publishing || !file || !form.title || selected.length === 0}
            className="w-full py-2.5 text-xs font-bold flex items-center justify-center gap-2 disabled:opacity-50"
            style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
            <Share2 className="w-3.5 h-3.5" />
            {publishing ? 'Publicando...' : `Publicar em ${selected.length} rede${selected.length !== 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}
