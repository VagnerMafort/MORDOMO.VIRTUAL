import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { X, Save, Server, Volume2, Key, Plus, Trash2, Eye, EyeOff, Download, Check, ArrowLeft, MessageCircle, Bot, Mic } from 'lucide-react';
import TelegramIntegration from '@/components/TelegramIntegration';

const SERVICE_OPTIONS = [
  { value: 'telegram', label: 'Telegram Bot Token' },
  { value: 'openai', label: 'OpenAI API Key' },
  { value: 'smtp_host', label: 'SMTP Host' },
  { value: 'smtp_port', label: 'SMTP Porta' },
  { value: 'smtp_user', label: 'SMTP Usuario' },
  { value: 'smtp_pass', label: 'SMTP Senha' },
  { value: 'github', label: 'GitHub Token' },
  { value: 'discord', label: 'Discord Bot Token' },
  { value: 'whatsapp', label: 'WhatsApp API Key' },
  { value: 'custom', label: 'Chave Personalizada' },
];

function CredentialsTab() {
  const { api } = useAuth();
  const [creds, setCreds] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [newCred, setNewCred] = useState({ name: '', service: 'telegram', key_value: '' });
  const [showValues, setShowValues] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/credentials');
        setCreds(data);
      } catch (e) { console.error(e); }
    })();
  }, [api]);

  const addCredential = async () => {
    if (!newCred.name.trim() || !newCred.key_value.trim()) return;
    setSaving(true);
    try {
      const { data } = await api.post('/credentials', newCred);
      setCreds(prev => [...prev, data]);
      setNewCred({ name: '', service: 'telegram', key_value: '' });
      setShowForm(false);
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const deleteCred = async (id) => {
    try {
      await api.delete(`/credentials/${id}`);
      setCreds(prev => prev.filter(c => c.id !== id));
    } catch (e) { console.error(e); }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Key className="w-4 h-4" style={{ color: 'var(--accent)' }} />
          <h3 className="text-sm font-semibold" style={{ fontFamily: 'Outfit, sans-serif' }}>Credenciais e Chaves de API</h3>
        </div>
        <button
          data-testid="add-credential-btn"
          onClick={() => setShowForm(!showForm)}
          className="p-1.5 transition-colors"
          style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <div className="p-4 flex flex-col gap-3 animate-fade-in" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
          <div>
            <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>Servico</label>
            <select
              data-testid="credential-service-select"
              value={newCred.service}
              onChange={e => setNewCred({ ...newCred, service: e.target.value })}
              className="w-full py-2 px-3 text-sm outline-none"
              style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
            >
              {SERVICE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>Nome/Descricao</label>
            <input
              data-testid="credential-name-input"
              value={newCred.name}
              onChange={e => setNewCred({ ...newCred, name: e.target.value })}
              className="w-full py-2 px-3 text-sm outline-none"
              style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
              placeholder="Ex: Bot do Telegram principal"
            />
          </div>
          <div>
            <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>Chave / Token</label>
            <input
              data-testid="credential-value-input"
              value={newCred.key_value}
              onChange={e => setNewCred({ ...newCred, key_value: e.target.value })}
              className="w-full py-2 px-3 text-sm outline-none font-mono"
              style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
              placeholder="Cole sua chave aqui..."
              type="password"
            />
          </div>
          <div className="flex gap-2">
            <button
              data-testid="save-credential-btn"
              onClick={addCredential}
              disabled={saving}
              className="flex-1 py-2 text-sm font-medium flex items-center justify-center gap-2 transition-colors"
              style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}
            >
              <Save className="w-3.5 h-3.5" /> {saving ? 'Salvando...' : 'Salvar'}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 text-sm transition-colors"
              style={{ border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Credentials list */}
      {creds.length === 0 && !showForm && (
        <p className="text-xs text-center py-4" style={{ color: 'var(--text-tertiary)' }}>
          Nenhuma credencial salva. Adicione suas chaves de API aqui.
        </p>
      )}
      {creds.map(cred => (
        <div
          key={cred.id}
          data-testid={`credential-item-${cred.id}`}
          className="flex items-center gap-3 p-3"
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs px-1.5 py-0.5 font-mono" style={{ background: 'rgba(255,214,0,0.15)', color: 'var(--accent)' }}>
                {cred.service}
              </span>
              <span className="text-sm truncate" style={{ color: 'var(--text-primary)' }}>{cred.name}</span>
            </div>
            <p className="text-xs font-mono mt-1" style={{ color: 'var(--text-tertiary)' }}>
              {showValues[cred.id] ? cred.key_value : cred.key_masked}
            </p>
          </div>
          <button
            onClick={() => setShowValues(prev => ({ ...prev, [cred.id]: !prev[cred.id] }))}
            className="p-1.5 transition-colors"
            style={{ color: 'var(--text-tertiary)' }}
          >
            {showValues[cred.id] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </button>
          <button
            data-testid={`delete-credential-${cred.id}`}
            onClick={() => deleteCred(cred.id)}
            className="p-1.5 transition-colors"
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--error)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text-tertiary)'}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}

function InstallBanner() {
  const [canInstall, setCanInstall] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    const handler = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setCanInstall(true);
    };
    window.addEventListener('beforeinstallprompt', handler);

    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setInstalled(true);
    }

    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const result = await deferredPrompt.userChoice;
    if (result.outcome === 'accepted') {
      setInstalled(true);
      setCanInstall(false);
    }
  };

  if (installed) {
    return (
      <div className="p-3 flex items-center gap-2" style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)' }}>
        <Check className="w-4 h-4" style={{ color: 'var(--success)' }} />
        <p className="text-xs" style={{ color: 'var(--success)' }}>App instalado como PWA</p>
      </div>
    );
  }

  return (
    <div className="p-3" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
      <div className="flex items-center gap-2 mb-2">
        <Download className="w-4 h-4" style={{ color: 'var(--accent)' }} />
        <h4 className="text-sm font-medium">Instalar como App</h4>
      </div>
      {canInstall ? (
        <button
          data-testid="install-pwa-btn"
          onClick={handleInstall}
          className="w-full py-2 text-sm font-medium flex items-center justify-center gap-2 transition-colors"
          style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}
        >
          <Download className="w-4 h-4" /> Instalar Mordomo Virtual
        </button>
      ) : (
        <div className="text-xs flex flex-col gap-1" style={{ color: 'var(--text-secondary)' }}>
          <p><strong>Android:</strong> Abra no Chrome &gt; Menu (3 pontos) &gt; "Adicionar a tela inicial"</p>
          <p><strong>iPhone:</strong> Abra no Safari &gt; Compartilhar &gt; "Adicionar a Tela de Inicio"</p>
          <p><strong>Desktop:</strong> Clique no icone de instalacao na barra de endereco</p>
        </div>
      )}
    </div>
  );
}

export default function SettingsPanel({ onClose }) {
  const { api } = useAuth();
  const [tab, setTab] = useState('general');
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/settings');
        setSettings(data);
      } catch (e) { console.error(e); }
    })();
  }, [api]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const { data } = await api.put('/settings', {
        ollama_url: settings.ollama_url,
        ollama_model: settings.ollama_model,
        ollama_model_fast: settings.ollama_model_fast,
        ollama_model_smart: settings.ollama_model_smart,
        tts_enabled: settings.tts_enabled,
        tts_language: settings.tts_language,
        agent_name: settings.agent_name,
        agent_personality: settings.agent_personality,
        wake_word_enabled: settings.wake_word_enabled,
      });
      setSettings(data);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const tabs = [
    { id: 'general', label: 'Geral' },
    { id: 'telegram', label: 'Telegram' },
    { id: 'credentials', label: 'Credenciais' },
    { id: 'install', label: 'Instalar' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div
        data-testid="settings-panel"
        className="w-full max-w-lg animate-fade-in max-h-[90vh] flex flex-col"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <button
              data-testid="settings-back-btn"
              onClick={onClose}
              className="p-1.5 transition-colors"
              style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-subtle)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <h2 className="text-lg font-bold tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>Configuracoes</h2>
          </div>
          <button data-testid="close-settings-btn" onClick={onClose} style={{ color: 'var(--text-tertiary)' }} className="p-1 transition-colors hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          {tabs.map(t => (
            <button
              key={t.id}
              data-testid={`settings-tab-${t.id}`}
              onClick={() => setTab(t.id)}
              className="flex-1 py-3 text-xs font-medium transition-colors"
              style={{
                color: tab === t.id ? 'var(--accent)' : 'var(--text-tertiary)',
                borderBottom: tab === t.id ? '2px solid var(--accent)' : '2px solid transparent',
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {tab === 'general' && settings && (
            <div className="flex flex-col gap-6">
              {/* Agent Identity */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Bot className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                  <h3 className="text-sm font-semibold" style={{ fontFamily: 'Outfit, sans-serif' }}>Identidade do Agente Principal</h3>
                </div>
                <div className="flex flex-col gap-3">
                  <div>
                    <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>Nome do Agente</label>
                    <input
                      data-testid="agent-name-setting"
                      value={settings.agent_name || ''}
                      onChange={e => setSettings({ ...settings, agent_name: e.target.value })}
                      className="w-full py-2.5 px-3 text-sm outline-none"
                      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                      placeholder="Mordomo Virtual"
                    />
                  </div>
                  <div>
                    <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>Personalidade / Instrucoes</label>
                    <textarea
                      data-testid="agent-personality-setting"
                      value={settings.agent_personality || ''}
                      onChange={e => setSettings({ ...settings, agent_personality: e.target.value })}
                      rows={4}
                      className="w-full py-2.5 px-3 text-sm outline-none resize-none"
                      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                      placeholder="Descreva a personalidade do seu agente. Ex: Voce e um assistente direto e objetivo, especialista em marketing digital..."
                    />
                    <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
                      Deixe vazio para usar a personalidade padrao do Mordomo Virtual
                    </p>
                  </div>
                </div>
              </div>

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
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                        Modelo Rapido <span className="text-xs" style={{ color: 'var(--success)' }}>(chat)</span>
                      </label>
                      <input
                        value={settings.ollama_model_fast || ''}
                        onChange={e => setSettings({ ...settings, ollama_model_fast: e.target.value })}
                        className="w-full py-2.5 px-3 text-sm outline-none font-mono"
                        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                        placeholder="qwen2.5:7b"
                      />
                    </div>
                    <div>
                      <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                        Modelo Inteligente <span className="text-xs" style={{ color: 'var(--accent)' }}>(complexo)</span>
                      </label>
                      <input
                        data-testid="ollama-model-input"
                        value={settings.ollama_model_smart || settings.ollama_model || ''}
                        onChange={e => setSettings({ ...settings, ollama_model_smart: e.target.value, ollama_model: e.target.value })}
                        className="w-full py-2.5 px-3 text-sm outline-none font-mono"
                        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                        placeholder="qwen2.5:32b"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Model recommendations */}
              <div className="p-3" style={{ background: 'var(--terminal-bg)', border: '1px solid var(--border-subtle)' }}>
                <p className="text-xs font-mono mb-2" style={{ color: 'var(--accent)' }}>Sistema de Modelo Dual:</p>
                <div className="flex flex-col gap-1 text-xs font-mono" style={{ color: 'var(--terminal-text)' }}>
                  <p>Rapido (7B)  - Chat, perguntas simples  ~3-5s</p>
                  <p>Inteligente (32B) - Mentorias, analises  ~15-30s</p>
                </div>
                <p className="text-xs font-mono mt-2" style={{ color: 'var(--text-tertiary)' }}>
                  O sistema detecta automaticamente a complexidade e escolhe o modelo ideal.
                </p>
              </div>

              {/* Voice Section */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Volume2 className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                  <h3 className="text-sm font-semibold" style={{ fontFamily: 'Outfit, sans-serif' }}>Voz e Audio</h3>
                </div>
                <div className="flex flex-col gap-2">
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
                      <span className="absolute top-0.5 w-4 h-4 transition-transform"
                        style={{ background: settings.tts_enabled ? 'var(--accent-text)' : 'var(--text-tertiary)', left: settings.tts_enabled ? '20px' : '2px' }} />
                    </button>
                  </div>
                  <div className="flex items-center justify-between p-3" style={{
                    background: settings.wake_word_enabled ? 'rgba(255,214,0,0.05)' : 'var(--bg-elevated)',
                    border: `1px solid ${settings.wake_word_enabled ? 'rgba(255,214,0,0.3)' : 'var(--border-subtle)'}`,
                  }}>
                    <div>
                      <div className="flex items-center gap-2">
                        <Mic className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
                        <p className="text-sm">Ativacao por Voz</p>
                      </div>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
                        Diga <strong>"Hey {settings.agent_name || 'Mordomo Virtual'}"</strong> para ativar
                      </p>
                    </div>
                    <button
                      data-testid="wake-word-toggle"
                      onClick={() => setSettings({ ...settings, wake_word_enabled: !settings.wake_word_enabled })}
                      className="w-10 h-6 flex-shrink-0 relative transition-colors"
                      style={{ background: settings.wake_word_enabled ? 'var(--accent)' : 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}
                    >
                      <span className="absolute top-0.5 w-4 h-4 transition-transform"
                        style={{ background: settings.wake_word_enabled ? 'var(--accent-text)' : 'var(--text-tertiary)', left: settings.wake_word_enabled ? '20px' : '2px' }} />
                    </button>
                  </div>
                  {settings.wake_word_enabled && (
                    <div className="p-2" style={{ background: 'var(--terminal-bg)', border: '1px solid var(--border-subtle)' }}>
                      <p className="text-xs font-mono" style={{ color: 'var(--terminal-text)' }}>
                        Escuta passiva ativa. O microfone fica ligado aguardando "Hey {settings.agent_name || 'Mordomo Virtual'}".
                        Ao detectar, entra no modo maos livres automaticamente.
                      </p>
                    </div>
                  )}
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

          {tab === 'telegram' && <TelegramIntegration />}

          {tab === 'credentials' && <CredentialsTab />}

          {tab === 'install' && (
            <div className="flex flex-col gap-4">
              <InstallBanner />
              <div className="p-3" style={{ background: 'var(--terminal-bg)', border: '1px solid var(--border-subtle)' }}>
                <p className="text-xs font-mono mb-2" style={{ color: 'var(--accent)' }}>Deploy na VPS com Docker:</p>
                <pre className="text-xs font-mono whitespace-pre-wrap" style={{ color: 'var(--terminal-text)' }}>
{`# 1. Clone o repositorio
git clone <repo-url> novaclaw
cd novaclaw

# 2. Configure o .env
cp backend/.env.example backend/.env
# Edite com suas credenciais

# 3. Instale Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5:32b

# 4. Inicie o backend
cd backend && pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001

# 5. Build e sirva o frontend
cd frontend && yarn && yarn build
# Sirva com nginx ou similar`}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
