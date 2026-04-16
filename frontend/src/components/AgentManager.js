import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { X, ArrowLeft, Plus, Trash2, Bot, Code, Search, BarChart3, Workflow, Pencil, Check, Play } from 'lucide-react';

const ICON_MAP = { Bot, Code, Search, BarChart3, Workflow };

export default function AgentManager({ onClose, onStartChat }) {
  const { api } = useAuth();
  const [agents, setAgents] = useState({ custom: [], templates: [] });
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', system_prompt: '', icon: 'Bot' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try { const { data } = await api.get('/agents'); setAgents(data); } catch (e) { console.error(e); }
    })();
  }, [api]);

  const createFromTemplate = async (templateId) => {
    try {
      const { data } = await api.post(`/agents/from-template/${templateId}`);
      setAgents(prev => ({ ...prev, custom: [...prev.custom, data] }));
    } catch (e) { console.error(e); }
  };

  const createCustom = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const { data } = await api.post('/agents', form);
      setAgents(prev => ({ ...prev, custom: [...prev.custom, data] }));
      setShowCreate(false);
      setForm({ name: '', description: '', system_prompt: '', icon: 'Bot' });
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const deleteAgent = async (id) => {
    try {
      await api.delete(`/agents/${id}`);
      setAgents(prev => ({ ...prev, custom: prev.custom.filter(a => a.id !== id) }));
    } catch (e) { console.error(e); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div data-testid="agent-manager" className="w-full max-w-2xl animate-fade-in max-h-[90vh] flex flex-col" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        {/* Header */}
        <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="p-1.5 transition-colors" style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <h2 className="text-lg font-bold tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>Meus Agentes</h2>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Crie agentes especializados para diferentes tarefas</p>
            </div>
          </div>
          <button onClick={onClose} style={{ color: 'var(--text-tertiary)' }} className="p-1"><X className="w-5 h-5" /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {/* My agents */}
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Seus Agentes</p>
            <button data-testid="create-agent-btn" onClick={() => setShowCreate(!showCreate)} className="p-1.5 transition-colors" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {/* Create form */}
          {showCreate && (
            <div className="mb-4 p-4 flex flex-col gap-3 animate-fade-in" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
              <input data-testid="agent-name-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="Nome do agente" className="w-full py-2 px-3 text-sm outline-none"
                style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
              <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                placeholder="Descricao curta" className="w-full py-2 px-3 text-sm outline-none"
                style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
              <textarea data-testid="agent-prompt-input" value={form.system_prompt} onChange={e => setForm({ ...form, system_prompt: e.target.value })}
                placeholder="Prompt do sistema - defina a personalidade e habilidades do agente..." rows={4}
                className="w-full py-2 px-3 text-sm outline-none resize-none"
                style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
              <div className="flex gap-2">
                <button data-testid="save-agent-btn" onClick={createCustom} disabled={saving}
                  className="flex-1 py-2 text-sm font-medium flex items-center justify-center gap-2"
                  style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
                  <Check className="w-3.5 h-3.5" /> {saving ? 'Criando...' : 'Criar Agente'}
                </button>
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm"
                  style={{ border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>Cancelar</button>
              </div>
            </div>
          )}

          {/* Custom agents list */}
          {agents.custom.length === 0 && !showCreate && (
            <p className="text-xs text-center py-4 mb-4" style={{ color: 'var(--text-tertiary)' }}>
              Nenhum agente criado. Use um template abaixo ou crie o seu.
            </p>
          )}
          <div className="flex flex-col gap-2 mb-6">
            {agents.custom.map(agent => {
              const Icon = ICON_MAP[agent.icon] || Bot;
              return (
                <div key={agent.id} data-testid={`agent-${agent.id}`}
                  className="flex items-center gap-3 p-3 group" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                  <div className="w-9 h-9 flex-shrink-0 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
                    <Icon className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{agent.name}</p>
                    <p className="text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>{agent.description || agent.system_prompt?.slice(0, 60)}</p>
                  </div>
                  <button data-testid={`chat-agent-${agent.id}`} onClick={() => onStartChat(agent)}
                    className="p-2 transition-colors" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}
                    title="Iniciar conversa">
                    <Play className="w-3.5 h-3.5" />
                  </button>
                  <button onClick={() => deleteAgent(agent.id)} className="p-2 transition-colors opacity-0 group-hover:opacity-100"
                    style={{ color: 'var(--text-tertiary)' }}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>

          {/* Templates */}
          <p className="text-xs font-medium uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>Templates Prontos</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {agents.templates.map(tmpl => {
              const Icon = ICON_MAP[tmpl.icon] || Bot;
              const alreadyCreated = agents.custom.some(a => a.name === tmpl.name);
              return (
                <div key={tmpl.id} data-testid={`template-${tmpl.id}`}
                  className="flex items-start gap-3 p-3 cursor-pointer transition-colors"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}
                  onClick={() => !alreadyCreated && createFromTemplate(tmpl.id)}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-subtle)'}>
                  <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center" style={{ background: 'rgba(255,214,0,0.1)', border: '1px solid rgba(255,214,0,0.3)' }}>
                    <Icon className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{tmpl.name}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>{tmpl.description}</p>
                    {alreadyCreated && <p className="text-xs mt-1" style={{ color: 'var(--success)' }}>Ja adicionado</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
