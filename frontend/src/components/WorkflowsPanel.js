import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  X, Workflow, Plus, Play, Trash2, Edit3, ChevronRight, CheckCircle2,
  XCircle, AlertCircle, History, Clock, Save
} from 'lucide-react';
import { toast } from 'sonner';

const SKILL_OPTIONS = [
  { value: 'web_search', label: 'Pesquisa na Internet', argsHint: '{"query":"..."}' },
  { value: 'gmail', label: 'Gmail', argsHint: '{"action":"list","query":"is:unread","max":5}' },
  { value: 'drive', label: 'Google Drive', argsHint: '{"action":"list"}' },
  { value: 'sheets', label: 'Google Sheets', argsHint: '{"action":"create","title":"...","values":[["A","B"]]}' },
  { value: 'calendar', label: 'Google Calendar', argsHint: '{"action":"list","days_ahead":7}' },
  { value: 'youtube', label: 'YouTube', argsHint: '{"action":"my_videos","max":10}' },
  { value: 'browser_automation', label: 'Automação Web (Playwright)', argsHint: '{"url":"https://...","actions":[{"type":"extract","selector":"h1","as":"text","var":"titulo"}]}' },
  { value: 'web_scraper', label: 'Web Scraper', argsHint: '{"url":"https://..."}' },
  { value: 'url_summarizer', label: 'Resumidor de URL', argsHint: '{"url":"https://..."}' },
  { value: 'code_executor', label: 'Executor de Código', argsHint: '{"code":"print(1+1)","language":"python"}' },
  { value: 'calculator', label: 'Calculadora', argsHint: '{"expression":"2+2"}' },
  { value: 'datetime_info', label: 'Data/Hora', argsHint: '{}' },
  { value: 'api_caller', label: 'Chamada de API', argsHint: '{"url":"https://api...","method":"GET"}' },
];

export default function WorkflowsPanel({ onClose }) {
  const { api } = useAuth();
  const [list, setList] = useState([]);
  const [editing, setEditing] = useState(null);
  const [showHistory, setShowHistory] = useState(false);

  const load = useCallback(async () => {
    try { const { data } = await api.get('/workflows'); setList(data); } catch {}
  }, [api]);
  useEffect(() => { load(); }, [load]);

  const runWorkflow = async (wf) => {
    toast.info(`Executando '${wf.name}'...`);
    try {
      const { data } = await api.post(`/workflows/${wf.id}/run`, { initial_vars: {} });
      const ok = data.status === 'success';
      toast[ok ? 'success' : 'error'](`Fluxo ${ok ? 'OK' : 'com erro'} — ${data.duration_ms}ms`);
      setShowHistory(true);
    } catch (e) { toast.error('Erro na execução'); }
  };

  const deleteWorkflow = async (wf) => {
    if (!window.confirm(`Excluir fluxo '${wf.name}'?`)) return;
    await api.delete(`/workflows/${wf.id}`);
    load();
  };

  return (
    <div data-testid="workflows-panel" className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}>
      <div className="w-full max-w-5xl h-full max-h-[92vh] flex flex-col overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
              <Workflow className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
            </div>
            <h2 className="text-sm font-bold tracking-wider uppercase" style={{ fontFamily: 'Outfit, sans-serif' }}>Fluxos de Trabalho</h2>
          </div>
          <div className="flex items-center gap-2">
            <button data-testid="toggle-history-btn" onClick={() => setShowHistory(!showHistory)} className="p-1.5 text-xs flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
              <History className="w-3.5 h-3.5" /> Histórico
            </button>
            <button data-testid="new-workflow-btn" onClick={() => setEditing({ name: '', description: '', steps: [], trigger: 'manual', active: true })} className="px-3 py-1.5 text-xs font-semibold flex items-center gap-1.5" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
              <Plus className="w-3.5 h-3.5" /> Novo
            </button>
            <button data-testid="workflows-close-btn" onClick={onClose} className="p-1.5 ml-2" style={{ color: 'var(--text-tertiary)' }}>
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5" style={{ background: 'var(--bg-base)' }}>
          {showHistory ? <HistoryTab api={api} /> : (
            list.length === 0 ? (
              <div className="text-center py-16">
                <Workflow className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
                <p className="text-sm mb-1" style={{ color: 'var(--text-secondary)' }}>Nenhum fluxo criado ainda</p>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Clique em "Novo" para criar seu primeiro fluxo automatizado</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                {list.map(wf => (
                  <div key={wf.id} data-testid={`workflow-card-${wf.id}`} className="p-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                    <div className="flex items-start justify-between mb-2">
                      <div className="min-w-0 flex-1">
                        <h3 className="text-sm font-bold truncate" style={{ fontFamily: 'Outfit, sans-serif' }}>{wf.name}</h3>
                        <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-tertiary)' }}>{wf.description || '—'}</p>
                      </div>
                      <span className="text-[10px] px-1.5 py-0.5" style={{ background: wf.active ? 'rgba(34,197,94,0.1)' : 'rgba(148,163,184,0.1)', color: wf.active ? 'var(--success)' : 'var(--text-tertiary)' }}>
                        {wf.active ? 'ATIVO' : 'INATIVO'}
                      </span>
                    </div>
                    <div className="text-[11px] mb-3 flex items-center gap-2 flex-wrap" style={{ color: 'var(--text-tertiary)' }}>
                      <span>{wf.steps.length} passos</span>
                      <span>·</span>
                      <span>trigger: {wf.trigger}</span>
                    </div>
                    <div className="flex gap-1.5">
                      <button data-testid={`run-wf-${wf.id}`} onClick={() => runWorkflow(wf)} className="flex-1 py-1.5 text-xs font-semibold flex items-center justify-center gap-1" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
                        <Play className="w-3 h-3" /> Executar
                      </button>
                      <button data-testid={`edit-wf-${wf.id}`} onClick={() => setEditing(wf)} className="px-3 py-1.5 text-xs" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                        <Edit3 className="w-3 h-3" />
                      </button>
                      <button data-testid={`delete-wf-${wf.id}`} onClick={() => deleteWorkflow(wf)} className="px-3 py-1.5 text-xs" style={{ background: 'var(--bg-elevated)', color: 'var(--error)' }}>
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      </div>

      {editing && <EditorModal api={api} workflow={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
    </div>
  );
}

// ─── Editor ──────────────────────────────────────────────────────────────────
function EditorModal({ api, workflow, onClose, onSaved }) {
  const [form, setForm] = useState({
    name: workflow.name || '',
    description: workflow.description || '',
    trigger: workflow.trigger || 'manual',
    active: workflow.active !== false,
    steps: (workflow.steps || []).map(s => ({ ...s, argsStr: JSON.stringify(s.args || {}, null, 2) })),
  });
  const isNew = !workflow.id;

  const addStep = () => {
    setForm(f => ({ ...f, steps: [...f.steps, { skill: 'web_search', argsStr: '{"query":""}', output_var: '', on_error: 'stop', label: '' }] }));
  };
  const updateStep = (idx, patch) => {
    setForm(f => ({ ...f, steps: f.steps.map((s, i) => i === idx ? { ...s, ...patch } : s) }));
  };
  const removeStep = (idx) => {
    setForm(f => ({ ...f, steps: f.steps.filter((_, i) => i !== idx) }));
  };

  const save = async () => {
    const steps = [];
    for (const s of form.steps) {
      let args = {};
      try { args = JSON.parse(s.argsStr || '{}'); }
      catch { toast.error(`JSON inválido no passo '${s.skill}'`); return; }
      steps.push({ skill: s.skill, args, output_var: s.output_var || null, on_error: s.on_error || 'stop', label: s.label || '' });
    }
    const payload = { name: form.name, description: form.description, trigger: form.trigger, active: form.active, steps };
    try {
      if (isNew) await api.post('/workflows', payload);
      else await api.put(`/workflows/${workflow.id}`, payload);
      toast.success('Fluxo salvo');
      onSaved();
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao salvar'); }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-3" style={{ background: 'rgba(0,0,0,0.75)' }}>
      <div className="w-full max-w-3xl max-h-[92vh] flex flex-col" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        <div className="flex items-center justify-between px-4 py-2.5 border-b" style={{ borderColor: 'var(--border-subtle)' }}>
          <h3 className="text-sm font-bold tracking-wider uppercase" style={{ fontFamily: 'Outfit, sans-serif' }}>{isNew ? 'Novo Fluxo' : `Editar: ${workflow.name}`}</h3>
          <button onClick={onClose} style={{ color: 'var(--text-tertiary)' }}><X className="w-4 h-4" /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ background: 'var(--bg-base)' }}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>Nome</label>
              <input data-testid="wf-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="w-full px-2 py-1.5 text-xs" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>Trigger</label>
              <select data-testid="wf-trigger" value={form.trigger} onChange={e => setForm({ ...form, trigger: e.target.value })} className="w-full px-2 py-1.5 text-xs" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
                <option value="manual">Manual</option>
                <option value="chat">Via Chat</option>
                <option value="schedule">Agendado</option>
                <option value="webhook">Webhook</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>Descrição</label>
            <input data-testid="wf-description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="w-full px-2 py-1.5 text-xs" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold tracking-wider uppercase" style={{ color: 'var(--text-secondary)' }}>Passos ({form.steps.length})</h4>
              <button data-testid="add-step-btn" onClick={addStep} className="px-2 py-1 text-[10px] flex items-center gap-1 font-semibold" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
                <Plus className="w-3 h-3" /> Novo passo
              </button>
            </div>
            <div className="space-y-2">
              {form.steps.map((s, idx) => (
                <StepEditor key={idx} idx={idx} step={s} onUpdate={patch => updateStep(idx, patch)} onRemove={() => removeStep(idx)} />
              ))}
              {form.steps.length === 0 && <p className="text-xs text-center py-4" style={{ color: 'var(--text-tertiary)' }}>Nenhum passo. Clique em "Novo passo".</p>}
            </div>
          </div>

          <div className="text-[11px] p-3" style={{ background: 'var(--bg-surface)', color: 'var(--text-tertiary)' }}>
            💡 <b>Dica:</b> Use <code>{'{{variavel}}'}</code> nos argumentos para referenciar <code>output_var</code> de passos anteriores.
          </div>
        </div>

        <div className="px-4 py-3 flex gap-2 border-t" style={{ borderColor: 'var(--border-subtle)' }}>
          <button data-testid="save-wf-btn" onClick={save} disabled={!form.name || form.steps.length === 0} className="flex-1 py-2 text-xs font-bold disabled:opacity-50 flex items-center justify-center gap-1.5" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
            <Save className="w-3.5 h-3.5" /> Salvar fluxo
          </button>
        </div>
      </div>
    </div>
  );
}

function StepEditor({ idx, step, onUpdate, onRemove }) {
  const skill = SKILL_OPTIONS.find(s => s.value === step.skill) || SKILL_OPTIONS[0];
  return (
    <div className="p-3 border" style={{ background: 'var(--bg-surface)', borderColor: 'var(--border-subtle)' }}>
      <div className="flex items-center gap-2 mb-2">
        <span className="w-5 h-5 flex items-center justify-center text-[10px] font-bold" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>{idx + 1}</span>
        <select value={step.skill} onChange={e => onUpdate({ skill: e.target.value, argsStr: SKILL_OPTIONS.find(s => s.value === e.target.value)?.argsHint || '{}' })}
          className="flex-1 px-2 py-1 text-xs" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
          {SKILL_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <button onClick={onRemove} className="p-1" style={{ color: 'var(--error)' }}><Trash2 className="w-3.5 h-3.5" /></button>
      </div>
      <input placeholder="Label (opcional)" value={step.label || ''} onChange={e => onUpdate({ label: e.target.value })}
        className="w-full px-2 py-1 text-xs mb-2" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
      <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>Args (JSON)</label>
      <textarea value={step.argsStr} onChange={e => onUpdate({ argsStr: e.target.value })} rows={3}
        className="w-full px-2 py-1 text-[11px] font-mono" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
      <div className="grid grid-cols-2 gap-2 mt-2">
        <input placeholder="output_var (salvar resultado como...)" value={step.output_var || ''} onChange={e => onUpdate({ output_var: e.target.value })}
          className="px-2 py-1 text-xs" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
        <select value={step.on_error || 'stop'} onChange={e => onUpdate({ on_error: e.target.value })}
          className="px-2 py-1 text-xs" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
          <option value="stop">Em erro: parar</option>
          <option value="continue">Em erro: continuar</option>
        </select>
      </div>
    </div>
  );
}

// ─── Histórico de execuções ──────────────────────────────────────────────────
function HistoryTab({ api }) {
  const [execs, setExecs] = useState([]);
  const [open, setOpen] = useState(null);
  const load = useCallback(async () => {
    try { const { data } = await api.get('/workflows/executions/recent?limit=50'); setExecs(data); } catch {}
  }, [api]);
  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <h3 className="text-xs font-bold tracking-wider uppercase mb-3" style={{ color: 'var(--text-secondary)' }}>Últimas execuções ({execs.length})</h3>
      <div className="space-y-1">
        {execs.length === 0 && <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Nenhuma execução.</p>}
        {execs.map(ex => {
          const Icon = ex.status === 'success' ? CheckCircle2 : ex.status === 'error' ? XCircle : AlertCircle;
          const color = ex.status === 'success' ? 'var(--success)' : ex.status === 'error' ? 'var(--error)' : 'var(--accent)';
          const isOpen = open === ex.id;
          return (
            <div key={ex.id} data-testid={`exec-${ex.id}`} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
              <button onClick={() => setOpen(isOpen ? null : ex.id)} className="w-full p-3 text-left flex items-center gap-3 text-xs">
                <Icon className="w-4 h-4 flex-shrink-0" style={{ color }} />
                <span className="font-bold" style={{ color: 'var(--text-primary)' }}>{ex.workflow_name}</span>
                <span className="flex-1" style={{ color: 'var(--text-tertiary)' }}>{new Date(ex.started_at).toLocaleString('pt-BR')}</span>
                <span style={{ color: 'var(--text-tertiary)' }}><Clock className="inline w-3 h-3 mr-1" />{ex.duration_ms}ms</span>
                <ChevronRight className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-90' : ''}`} style={{ color: 'var(--text-tertiary)' }} />
              </button>
              {isOpen && (
                <div className="border-t px-3 py-2 space-y-1.5" style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-base)' }}>
                  {ex.steps.map((s, i) => (
                    <div key={i} className="flex items-start gap-2 text-[11px]">
                      <span className="w-4 flex-shrink-0 font-bold" style={{ color: 'var(--text-tertiary)' }}>{i + 1}.</span>
                      <span className="font-bold w-28 flex-shrink-0" style={{ color: s.status === 'ok' ? 'var(--success)' : 'var(--error)' }}>{s.label}</span>
                      <span className="flex-1" style={{ color: 'var(--text-secondary)' }}>{s.output}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
