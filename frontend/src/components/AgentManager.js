import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  X, ArrowLeft, Plus, Trash2, Bot, Code, Search, BarChart3, Workflow,
  Check, Play, Shield, Crosshair, GitBranch, DollarSign, Target, Mail,
  Sparkles, Compass, Layout, MousePointer, TrendingUp, Package, FileText,
  Cpu, CheckCircle, Database, Brain, Handshake
} from 'lucide-react';

const ICON_MAP = {
  Bot, Code, Search, BarChart3, Workflow, Shield, Crosshair, GitBranch,
  DollarSign, Target, Mail, Sparkles, Compass, Layout, MousePointer,
  TrendingUp, Package, FileText, Cpu, CheckCircle, Database, Brain,
  Play, Handshake,
};

const SQUADS = [
  { name: 'Core & Governance', ids: ['orion', 'sentinel', 'exec_agent'] },
  { name: 'Data & Diagnostics', ids: ['dash', 'track', 'attrib'] },
  { name: 'Traffic & Performance', ids: ['midas'] },
  { name: 'Funnel & Sales', ids: ['hunter', 'lns', 'closer'] },
  { name: 'Creative & Messaging', ids: ['nova', 'mara'] },
  { name: 'Pages & Conversion', ids: ['lpx', 'dex', 'oubas', 'rex'] },
  { name: 'Research & Product', ids: ['atlas', 'moira'] },
  { name: 'Reporting & Finance', ids: ['finn', 'echo'] },
  { name: 'Sistema', ids: ['nero', 'eval_agent', 'archivist', 'learner'] },
  { name: 'Geral', ids: ['coder'] },
];

export default function AgentManager({ onClose, onStartChat }) {
  const { api } = useAuth();
  const [agents, setAgents] = useState({ custom: [], templates: [] });
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', system_prompt: '', icon: 'Bot' });
  const [saving, setSaving] = useState(false);
  const [searchQ, setSearchQ] = useState('');

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

  const createdNames = new Set(agents.custom.map(a => a.name));
  const filteredTemplates = agents.templates.filter(t =>
    !searchQ || t.name.toLowerCase().includes(searchQ.toLowerCase()) || t.description.toLowerCase().includes(searchQ.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div data-testid="agent-manager" className="w-full max-w-3xl animate-fade-in max-h-[90vh] flex flex-col" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        {/* Header */}
        <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="p-1.5 transition-colors" style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <h2 className="text-lg font-bold tracking-tight" style={{ fontFamily: 'Outfit' }}>Agentes da Agencia</h2>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>24 agentes especializados + seus agentes customizados</p>
            </div>
          </div>
          <button onClick={onClose} style={{ color: 'var(--text-tertiary)' }} className="p-1"><X className="w-5 h-5" /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {/* My agents */}
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--accent)' }}>Seus Agentes Ativos ({agents.custom.length})</p>
            <button data-testid="create-agent-btn" onClick={() => setShowCreate(!showCreate)}
              className="p-1.5" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {showCreate && (
            <div className="mb-4 p-4 flex flex-col gap-3 animate-fade-in" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
              <input data-testid="agent-name-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="Nome do agente" className="w-full py-2 px-3 text-sm outline-none"
                style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
              <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                placeholder="Descricao curta" className="w-full py-2 px-3 text-sm outline-none"
                style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
              <textarea data-testid="agent-prompt-input" value={form.system_prompt} onChange={e => setForm({ ...form, system_prompt: e.target.value })}
                placeholder="Prompt do sistema..." rows={3} className="w-full py-2 px-3 text-sm outline-none resize-none"
                style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
              <div className="flex gap-2">
                <button onClick={createCustom} disabled={saving} className="flex-1 py-2 text-sm font-medium flex items-center justify-center gap-2"
                  style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
                  <Check className="w-3.5 h-3.5" /> {saving ? 'Criando...' : 'Criar'}
                </button>
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm"
                  style={{ border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>Cancelar</button>
              </div>
            </div>
          )}

          {agents.custom.length > 0 && (
            <div className="flex flex-col gap-1.5 mb-6">
              {agents.custom.map(agent => {
                const Icon = ICON_MAP[agent.icon] || Bot;
                return (
                  <div key={agent.id} data-testid={`agent-${agent.id}`}
                    className="flex items-center gap-3 p-2.5 group" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                    <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
                      <Icon className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{agent.name}</p>
                      <p className="text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>{agent.description}</p>
                    </div>
                    <button onClick={() => onStartChat(agent)} className="p-1.5" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }} title="Conversar">
                      <Play className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={() => deleteAgent(agent.id)} className="p-1.5 opacity-0 group-hover:opacity-100"
                      style={{ color: 'var(--text-tertiary)' }}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {/* Search templates */}
          <input value={searchQ} onChange={e => setSearchQ(e.target.value)}
            placeholder="Buscar agente..." className="w-full py-2 px-3 text-sm outline-none mb-4"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />

          {/* Templates by squad */}
          {SQUADS.map(squad => {
            const squadTemplates = filteredTemplates.filter(t => squad.ids.includes(t.id));
            if (squadTemplates.length === 0) return null;
            return (
              <div key={squad.name} className="mb-4">
                <p className="text-xs font-medium uppercase tracking-wider mb-2" style={{ color: 'var(--text-tertiary)' }}>
                  {squad.name}
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  {squadTemplates.map(tmpl => {
                    const Icon = ICON_MAP[tmpl.icon] || Bot;
                    const added = createdNames.has(tmpl.name);
                    return (
                      <div key={tmpl.id} data-testid={`template-${tmpl.id}`}
                        className={`flex items-center gap-2.5 p-2.5 transition-colors ${added ? '' : 'cursor-pointer'}`}
                        style={{ background: added ? 'rgba(255,214,0,0.03)' : 'var(--bg-elevated)', border: `1px solid ${added ? 'rgba(255,214,0,0.2)' : 'var(--border-subtle)'}` }}
                        onClick={() => !added && createFromTemplate(tmpl.id)}>
                        <div className="w-7 h-7 flex-shrink-0 flex items-center justify-center"
                          style={{ background: added ? 'var(--accent)' : 'rgba(255,214,0,0.08)', border: added ? 'none' : '1px solid rgba(255,214,0,0.2)' }}>
                          <Icon className="w-3.5 h-3.5" style={{ color: added ? 'var(--accent-text)' : 'var(--accent)' }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium truncate">{tmpl.name}</p>
                          <p className="text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>{tmpl.description.slice(0, 60)}</p>
                        </div>
                        {added && <Check className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--success)' }} />}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
