import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { X, Save, Server, Bot, Volume2 } from 'lucide-react';

export default function SettingsPanel({ onClose }) {
  const { api } = useAuth();
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/settings');
        setSettings(data);
      } catch (e) {
        console.error(e);
      }
    })();
  }, [api]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const { data } = await api.put('/settings', {
        ollama_url: settings.ollama_url,
        ollama_model: settings.ollama_model,
        tts_enabled: settings.tts_enabled,
        tts_language: settings.tts_language,
      });
      setSettings(data);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div
        data-testid="settings-panel"
        className="w-full max-w-lg animate-fade-in max-h-[85vh] overflow-y-auto"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <h2 className="text-lg font-bold tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>Configuracoes</h2>
          <button data-testid="close-settings-btn" onClick={onClose} style={{ color: 'var(--text-tertiary)' }} className="p-1 transition-colors hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {settings && (
          <div className="p-5 flex flex-col gap-6">
            {/* Ollama Section */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Server className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                <h3 className="text-sm font-semibold" style={{ fontFamily: 'Outfit, sans-serif' }}>Conexao Ollama</h3>
              </div>
              <div className="flex flex-col gap-3">
                <div>
                  <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>URL da API Ollama</label>
                  <input
                    data-testid="ollama-url-input"
                    value={settings.ollama_url || ''}
                    onChange={e => setSettings({ ...settings, ollama_url: e.target.value })}
                    className="w-full py-2.5 px-3 text-sm outline-none font-mono"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                    placeholder="http://localhost:11434"
                  />
                </div>
                <div>
                  <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>Modelo</label>
                  <input
                    data-testid="ollama-model-input"
                    value={settings.ollama_model || ''}
                    onChange={e => setSettings({ ...settings, ollama_model: e.target.value })}
                    className="w-full py-2.5 px-3 text-sm outline-none font-mono"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                    placeholder="qwen2.5:32b"
                  />
                </div>
              </div>
            </div>

            {/* Model recommendations */}
            <div className="p-3" style={{ background: 'var(--terminal-bg)', border: '1px solid var(--border-subtle)' }}>
              <p className="text-xs font-mono mb-2" style={{ color: 'var(--terminal-text)' }}>Modelos recomendados (48GB RAM, sem GPU):</p>
              <div className="flex flex-col gap-1 text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                <p>qwen2.5:32b-q4_K_M  ~20GB - Recomendado</p>
                <p>qwen2.5:14b-q4_K_M  ~10GB - Equilibrado</p>
                <p>mistral:7b-q4_K_M   ~5GB  - Leve e rapido</p>
                <p>llama3.1:8b-q4_K_M  ~6GB  - Boa performance</p>
              </div>
            </div>

            {/* TTS Section */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Volume2 className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                <h3 className="text-sm font-semibold" style={{ fontFamily: 'Outfit, sans-serif' }}>Voz e Audio</h3>
              </div>
              <div className="flex items-center justify-between p-3" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                <div>
                  <p className="text-sm">Leitura de Respostas (TTS)</p>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>O agente le as respostas em voz alta</p>
                </div>
                <button
                  data-testid="tts-toggle"
                  onClick={() => setSettings({ ...settings, tts_enabled: !settings.tts_enabled })}
                  className="w-10 h-6 flex-shrink-0 relative transition-colors"
                  style={{ background: settings.tts_enabled ? 'var(--accent)' : 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}
                >
                  <span
                    className="absolute top-0.5 w-4 h-4 transition-transform"
                    style={{
                      background: settings.tts_enabled ? 'var(--accent-text)' : 'var(--text-tertiary)',
                      left: settings.tts_enabled ? '20px' : '2px'
                    }}
                  />
                </button>
              </div>
            </div>

            {/* Save */}
            <button
              data-testid="save-settings-btn"
              onClick={handleSave}
              disabled={saving}
              className="w-full py-3 px-6 text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
              style={{ background: saved ? 'var(--success)' : 'var(--accent)', color: saved ? 'white' : 'var(--accent-text)' }}
            >
              <Save className="w-4 h-4" />
              {saved ? 'Salvo!' : saving ? 'Salvando...' : 'Salvar Configuracoes'}
            </button>

            {/* Install guide */}
            <div className="p-3" style={{ background: 'var(--terminal-bg)', border: '1px solid var(--border-subtle)' }}>
              <p className="text-xs font-mono mb-2" style={{ color: 'var(--accent)' }}>Instalar Ollama na VPS:</p>
              <pre className="text-xs font-mono" style={{ color: 'var(--terminal-text)' }}>
{`curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5:32b
ollama serve`}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
