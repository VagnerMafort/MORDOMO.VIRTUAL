import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { X, Brain, Plus, Trash2, Zap, Play, CheckCircle2, AlertTriangle, FileText, Users, Activity, RefreshCw, Shield, Sparkles, Rocket } from 'lucide-react';
import { toast } from 'sonner';

export default function JamesPanel({ onClose }) {
  const { api } = useAuth();
  const [tab, setTab] = useState('products'); // products | agents | anomalies | plans | reports | learnings
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [agents, setAgents] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [plans, setPlans] = useState([]);
  const [reports, setReports] = useState([]);
  const [learnings, setLearnings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newProduct, setNewProduct] = useState({ name: '', niche: '', target_audience: '', offer: '', budget_daily: 0 });
  const [showNewProduct, setShowNewProduct] = useState(false);
  const [autopilotProduct, setAutopilotProduct] = useState(null);  // produto sendo configurado
  const [autopilotConfig, setAutopilotConfig] = useState(null);

  const loadProducts = useCallback(async () => {
    try { const { data } = await api.get('/james/products'); setProducts(data); } catch {}
  }, [api]);
  const loadAgents = useCallback(async () => {
    try { const { data } = await api.get('/james/agents'); setAgents(data.agents); } catch {}
  }, [api]);
  const loadAnomalies = useCallback(async (pid) => {
    if (!pid) { setAnomalies([]); return; }
    try { const { data } = await api.get(`/james/products/${pid}/anomalies`); setAnomalies(data); } catch {}
  }, [api]);
  const loadPlans = useCallback(async (pid) => {
    if (!pid) { setPlans([]); return; }
    try { const { data } = await api.get(`/james/products/${pid}/plans`); setPlans(data); } catch {}
  }, [api]);
  const loadReports = useCallback(async () => {
    try { const { data } = await api.get('/james/reports'); setReports(data); } catch {}
  }, [api]);
  const loadLearnings = useCallback(async () => {
    try { const { data } = await api.get('/james/learnings'); setLearnings(data); } catch {}
  }, [api]);

  useEffect(() => { loadProducts(); loadAgents(); }, [loadProducts, loadAgents]);
  useEffect(() => {
    if (!selectedProduct) return;
    if (tab === 'anomalies') loadAnomalies(selectedProduct.id);
    if (tab === 'plans') loadPlans(selectedProduct.id);
  }, [tab, selectedProduct, loadAnomalies, loadPlans]);
  useEffect(() => { if (tab === 'reports') loadReports(); }, [tab, loadReports]);
  useEffect(() => { if (tab === 'learnings') loadLearnings(); }, [tab, loadLearnings]);

  const createProduct = async () => {
    if (!newProduct.name.trim()) return toast.error('Nome obrigatório');
    setLoading(true);
    try {
      const { data } = await api.post('/james/products', newProduct);
      toast.success(`Produto ${data.name} criado`);
      setShowNewProduct(false);
      setNewProduct({ name: '', niche: '', target_audience: '', offer: '', budget_daily: 0 });
      loadProducts();
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro'); }
    setLoading(false);
  };

  const deleteProduct = async (p) => {
    if (!window.confirm(`Remover "${p.name}"? Métricas e anomalias serão apagadas.`)) return;
    await api.delete(`/james/products/${p.id}`);
    toast.success('Removido');
    if (selectedProduct?.id === p.id) setSelectedProduct(null);
    loadProducts();
  };

  const seedProduct = async (pid) => {
    setLoading(true);
    try {
      const { data } = await api.post(`/james/products/${pid}/seed?days=7&anomaly=true`);
      toast.success(`${data.inserted} métricas + 1 anomalia injetadas`);
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro'); }
    setLoading(false);
  };

  const runTick = async (pid, evaluate = false) => {
    setLoading(true);
    try {
      const { data } = await api.post(`/james/products/${pid}/tick?evaluate=${evaluate}`);
      toast.success(`Tick: ${data.anomalies_detected} anomalias · ${data.plans_created.length} planos · ${data.executed?.length || 0} executados`);
      if (tab === 'anomalies') loadAnomalies(pid);
      if (tab === 'plans') loadPlans(pid);
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro no tick'); }
    setLoading(false);
  };

  const approveAndRun = async (planId) => {
    setLoading(true);
    try {
      await api.post(`/james/plans/${planId}/approve`);
      const { data } = await api.post(`/james/plans/${planId}/run`);
      toast.success(`Executado: ${data.execution?.status} · Avaliação: ${data.evaluation?.result}`);
      if (selectedProduct) loadPlans(selectedProduct.id);
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao executar'); }
    setLoading(false);
  };

  const generateReport = async () => {
    setLoading(true);
    try {
      const body = { product_id: selectedProduct?.id || null, level: selectedProduct ? 'product' : 'agency', period_hours: 168 };
      const { data } = await api.post('/james/reports/generate', body);
      toast.success('Relatório gerado por ECHO');
      loadReports();
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro'); }
    setLoading(false);
  };

  const openAutopilot = async (p) => {
    try {
      const { data } = await api.get(`/james/products/${p.id}/autopilot`);
      setAutopilotProduct(p);
      setAutopilotConfig(data);
    } catch (e) { toast.error('Erro ao carregar config'); }
  };

  const saveAutopilot = async () => {
    if (!autopilotProduct) return;
    setLoading(true);
    try {
      await api.put(`/james/products/${autopilotProduct.id}/autopilot`, autopilotConfig);
      toast.success(autopilotConfig.autopilot_enabled ? 'Autopilot ATIVADO — rodando 24/7' : 'Autopilot desativado');
      loadProducts();
      setAutopilotProduct(null);
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro'); }
    setLoading(false);
  };

  const SEV_STYLE = {
    low: { bg: 'rgba(148,163,184,0.15)', fg: 'var(--text-tertiary)' },
    medium: { bg: 'rgba(234,179,8,0.15)', fg: '#eab308' },
    high: { bg: 'rgba(239,68,68,0.15)', fg: 'var(--error)' },
    critical: { bg: 'rgba(220,38,38,0.25)', fg: '#ef4444' },
  };

  const STATUS_STYLE = {
    new: { bg: 'rgba(148,163,184,0.1)', fg: 'var(--text-tertiary)' },
    prioritized: { bg: 'rgba(234,179,8,0.15)', fg: '#eab308' },
    assigned: { bg: 'rgba(59,130,246,0.15)', fg: '#3b82f6' },
    resolved: { bg: 'rgba(34,197,94,0.15)', fg: 'var(--success)' },
    ignored: { bg: 'rgba(148,163,184,0.1)', fg: 'var(--text-tertiary)' },
    validated: { bg: 'rgba(59,130,246,0.15)', fg: '#3b82f6' },
    approved: { bg: 'rgba(234,179,8,0.15)', fg: '#eab308' },
    executing: { bg: 'rgba(234,179,8,0.2)', fg: '#eab308' },
    done: { bg: 'rgba(34,197,94,0.15)', fg: 'var(--success)' },
    failed: { bg: 'rgba(239,68,68,0.15)', fg: 'var(--error)' },
    blocked: { bg: 'rgba(239,68,68,0.15)', fg: 'var(--error)' },
  };

  const agentsGrouped = agents.reduce((acc, a) => {
    if (!acc[a.squad]) acc[a.squad] = [];
    acc[a.squad].push(a);
    return acc;
  }, {});

  return (
    <div data-testid="james-panel" className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}>
      <div className="w-full max-w-6xl h-full max-h-[92vh] flex flex-col overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
              <Brain className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-wider uppercase" style={{ fontFamily: 'Outfit, sans-serif' }}>JAMES Agency</h2>
              <p className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>24 agentes · 14 camadas · Sistema autônomo</p>
            </div>
          </div>
          <button data-testid="james-close-btn" onClick={onClose} className="p-1.5" style={{ color: 'var(--text-tertiary)' }}>
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-3 py-2 overflow-x-auto" style={{ borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-base)' }}>
          {[
            { id: 'products', label: 'Produtos', icon: Users },
            { id: 'agents', label: '24 Agentes', icon: Brain },
            { id: 'anomalies', label: 'Anomalias', icon: AlertTriangle },
            { id: 'plans', label: 'Planos', icon: Zap },
            { id: 'reports', label: 'Relatórios', icon: FileText },
            { id: 'learnings', label: 'Aprendizados', icon: Sparkles },
          ].map(({ id, label, icon: Ic }) => (
            <button
              key={id}
              data-testid={`james-tab-${id}`}
              onClick={() => setTab(id)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold whitespace-nowrap"
              style={{
                background: tab === id ? 'var(--accent)' : 'transparent',
                color: tab === id ? 'var(--accent-text)' : 'var(--text-secondary)',
              }}
            >
              <Ic className="w-3.5 h-3.5" /> {label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5" style={{ background: 'var(--bg-base)' }}>

          {/* PRODUCTS TAB */}
          {tab === 'products' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{products.length} produto(s)</p>
                <button data-testid="james-new-product-btn" onClick={() => setShowNewProduct(true)} className="flex items-center gap-2 px-3 py-1.5 text-xs font-bold" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
                  <Plus className="w-3.5 h-3.5" /> Novo Produto
                </button>
              </div>

              {showNewProduct && (
                <div className="p-4 space-y-3" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                  <input data-testid="new-product-name" value={newProduct.name} onChange={e => setNewProduct({ ...newProduct, name: e.target.value })} placeholder="Nome do produto" className="w-full px-3 py-2 text-sm" style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', border: '1px solid var(--border-subtle)' }} />
                  <input value={newProduct.niche} onChange={e => setNewProduct({ ...newProduct, niche: e.target.value })} placeholder="Nicho" className="w-full px-3 py-2 text-sm" style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', border: '1px solid var(--border-subtle)' }} />
                  <input value={newProduct.target_audience} onChange={e => setNewProduct({ ...newProduct, target_audience: e.target.value })} placeholder="Público-alvo" className="w-full px-3 py-2 text-sm" style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', border: '1px solid var(--border-subtle)' }} />
                  <input value={newProduct.offer} onChange={e => setNewProduct({ ...newProduct, offer: e.target.value })} placeholder="Oferta" className="w-full px-3 py-2 text-sm" style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', border: '1px solid var(--border-subtle)' }} />
                  <input type="number" value={newProduct.budget_daily} onChange={e => setNewProduct({ ...newProduct, budget_daily: parseFloat(e.target.value) || 0 })} placeholder="Budget diário" className="w-full px-3 py-2 text-sm" style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', border: '1px solid var(--border-subtle)' }} />
                  <div className="flex gap-2">
                    <button data-testid="save-product-btn" onClick={createProduct} disabled={loading} className="flex-1 py-2 text-xs font-bold disabled:opacity-50" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>{loading ? 'Criando...' : 'Criar'}</button>
                    <button onClick={() => setShowNewProduct(false)} className="px-4 py-2 text-xs font-bold" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>Cancelar</button>
                  </div>
                </div>
              )}

              {products.map(p => (
                <div key={p.id} data-testid={`product-${p.id}`} className="p-4" style={{ background: selectedProduct?.id === p.id ? 'var(--bg-elevated)' : 'var(--bg-surface)', border: `1px solid ${selectedProduct?.id === p.id ? 'var(--accent)' : 'var(--border-subtle)'}` }}>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div onClick={() => setSelectedProduct(p)} className="cursor-pointer flex-1">
                      <p className="text-sm font-bold" style={{ color: 'var(--text-primary)', fontFamily: 'Outfit, sans-serif' }}>{p.name}</p>
                      <p className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>{p.niche || 'sem nicho'} · budget R$ {p.budget_daily}/dia</p>
                    </div>
                    <button onClick={() => deleteProduct(p)} className="p-1.5" style={{ color: 'var(--error)' }}><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    <button data-testid={`seed-${p.id}`} onClick={() => seedProduct(p.id)} className="flex items-center gap-1 px-2 py-1 text-[10px] font-bold" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                      <Activity className="w-3 h-3" /> Seed Demo
                    </button>
                    <button data-testid={`tick-${p.id}`} onClick={() => runTick(p.id, false)} disabled={loading} className="flex items-center gap-1 px-2 py-1 text-[10px] font-bold disabled:opacity-50" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
                      <RefreshCw className="w-3 h-3" /> Tick
                    </button>
                    <button onClick={() => runTick(p.id, true)} disabled={loading} className="flex items-center gap-1 px-2 py-1 text-[10px] font-bold disabled:opacity-50" style={{ background: 'var(--success)', color: '#0b1220' }}>
                      <Play className="w-3 h-3" /> Tick + Run
                    </button>
                    <button
                      data-testid={`autopilot-${p.id}`}
                      onClick={() => openAutopilot(p)}
                      className="flex items-center gap-1 px-2 py-1 text-[10px] font-bold"
                      style={{
                        background: p.autopilot_enabled ? 'rgba(34,197,94,0.15)' : 'var(--bg-base)',
                        border: `1px solid ${p.autopilot_enabled ? 'var(--success)' : 'var(--border-subtle)'}`,
                        color: p.autopilot_enabled ? 'var(--success)' : 'var(--text-secondary)',
                      }}
                    >
                      <Rocket className="w-3 h-3" /> {p.autopilot_enabled ? 'Autopilot ATIVO 24/7' : 'Ativar Autopilot 24/7'}
                    </button>
                  </div>
                </div>
              ))}
              {products.length === 0 && !showNewProduct && (
                <p className="text-center text-xs py-8" style={{ color: 'var(--text-tertiary)' }}>Nenhum produto. Crie um pra começar.</p>
              )}
            </div>
          )}

          {/* AGENTS TAB */}
          {tab === 'agents' && (
            <div className="space-y-4">
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{agents.length} agentes organizados em 8 squads</p>
              {Object.keys(agentsGrouped).sort().map(squad => (
                <div key={squad}>
                  <p className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--accent)' }}>{squad}</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {agentsGrouped[squad].map(a => (
                      <div key={a.code} data-testid={`agent-${a.code}`} className="p-3" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-sm font-bold" style={{ color: 'var(--text-primary)', fontFamily: 'Outfit, sans-serif' }}>{a.code}</p>
                          <span className="text-[10px] px-1.5 py-0.5" style={{ background: 'rgba(255,214,0,0.15)', color: 'var(--accent)' }}>{a.phase}</span>
                        </div>
                        <p className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>{a.role}</p>
                        {a.skills?.length > 0 && (
                          <p className="text-[10px] mt-1" style={{ color: 'var(--text-tertiary)' }}>skills: {a.skills.join(', ')}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ANOMALIES TAB */}
          {tab === 'anomalies' && (
            <div className="space-y-2">
              {!selectedProduct ? (
                <p className="text-xs py-8 text-center" style={{ color: 'var(--text-tertiary)' }}>Selecione um produto na aba "Produtos"</p>
              ) : anomalies.length === 0 ? (
                <p className="text-xs py-8 text-center" style={{ color: 'var(--text-tertiary)' }}>Nenhuma anomalia detectada. Rode um tick.</p>
              ) : anomalies.map(a => (
                <div key={a.id} data-testid={`anomaly-${a.id}`} className="p-3" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" style={{ color: SEV_STYLE[a.severity]?.fg }} />
                      <p className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>{a.metric.toUpperCase()} {a.kind}</p>
                      <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase" style={{ background: SEV_STYLE[a.severity]?.bg, color: SEV_STYLE[a.severity]?.fg }}>{a.severity}</span>
                      <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase" style={{ background: STATUS_STYLE[a.status]?.bg, color: STATUS_STYLE[a.status]?.fg }}>{a.status}</span>
                    </div>
                    {a.assigned_agent && (<span className="text-[10px] font-bold" style={{ color: 'var(--accent)' }}>→ {a.assigned_agent}</span>)}
                  </div>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{a.description}</p>
                  <p className="text-[11px] mt-1" style={{ color: 'var(--text-tertiary)' }}>atual {a.current_value.toFixed(2)} · esperado {a.expected_value.toFixed(2)} · prioridade {a.priority_score?.toFixed(1)}</p>
                </div>
              ))}
            </div>
          )}

          {/* PLANS TAB */}
          {tab === 'plans' && (
            <div className="space-y-2">
              {!selectedProduct ? (
                <p className="text-xs py-8 text-center" style={{ color: 'var(--text-tertiary)' }}>Selecione um produto</p>
              ) : plans.length === 0 ? (
                <p className="text-xs py-8 text-center" style={{ color: 'var(--text-tertiary)' }}>Nenhum plano gerado ainda.</p>
              ) : plans.map(p => (
                <div key={p.id} data-testid={`plan-${p.id}`} className="p-3" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold px-2 py-0.5" style={{ background: 'rgba(255,214,0,0.15)', color: 'var(--accent)' }}>{p.agent}</span>
                      <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{p.objective}</p>
                      <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase" style={{ background: STATUS_STYLE[p.status]?.bg, color: STATUS_STYLE[p.status]?.fg }}>{p.status}</span>
                      {p.guardrails_passed && <span title="Guardrails OK"><Shield className="w-3 h-3 inline" style={{ color: 'var(--success)' }} /></span>}
                    </div>
                  </div>
                  <ul className="mt-1 space-y-0.5 pl-4">
                    {p.steps?.map((s, i) => (
                      <li key={i} className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                        {s.order}. <code>{s.action}</code> {s.rationale && <span style={{ color: 'var(--text-tertiary)' }}>— {s.rationale}</span>}
                      </li>
                    ))}
                  </ul>
                  {p.status === 'validated' && (
                    <button data-testid={`approve-run-${p.id}`} onClick={() => approveAndRun(p.id)} disabled={loading} className="mt-2 flex items-center gap-1 px-3 py-1 text-[11px] font-bold disabled:opacity-50" style={{ background: 'var(--success)', color: '#0b1220' }}>
                      <CheckCircle2 className="w-3 h-3" /> Aprovar + Executar
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* REPORTS TAB */}
          {tab === 'reports' && (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Produto ativo: {selectedProduct?.name || '(todos)'}</p>
                <button data-testid="generate-report-btn" onClick={generateReport} disabled={loading} className="flex items-center gap-1 px-3 py-1.5 text-xs font-bold disabled:opacity-50" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
                  <FileText className="w-3.5 h-3.5" /> Gerar (ECHO)
                </button>
              </div>
              {reports.map(r => (
                <div key={r.id} data-testid={`report-${r.id}`} className="p-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5" style={{ background: 'rgba(255,214,0,0.15)', color: 'var(--accent)' }}>{r.level}</span>
                    <span className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>{new Date(r.generated_at).toLocaleString('pt-BR')}</span>
                  </div>
                  <div className="mb-3 flex flex-wrap gap-3 text-[11px]">
                    {Object.entries(r.kpis || {}).slice(0, 6).map(([k, v]) => (
                      <span key={k} style={{ color: 'var(--text-secondary)' }}><b style={{ color: 'var(--text-primary)' }}>{k}</b>: {v}</span>
                    ))}
                  </div>
                  <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>{r.narrative}</p>
                </div>
              ))}
              {reports.length === 0 && <p className="text-xs py-8 text-center" style={{ color: 'var(--text-tertiary)' }}>Nenhum relatório. Gere um.</p>}
            </div>
          )}

          {/* LEARNINGS TAB */}
          {tab === 'learnings' && (
            <div className="space-y-2">
              {learnings.map(l => (
                <div key={l.id} className="p-3" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5" style={{ background: 'rgba(59,130,246,0.15)', color: '#3b82f6' }}>{l.level}</span>
                    <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{l.key}</p>
                    <span className="text-[11px]" style={{ color: l.success_rate >= 0.5 ? 'var(--success)' : 'var(--error)' }}>
                      {(l.success_rate * 100).toFixed(0)}% sucesso · {l.samples} amostra(s)
                    </span>
                  </div>
                  <p className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>{l.pattern}</p>
                </div>
              ))}
              {learnings.length === 0 && <p className="text-xs py-8 text-center" style={{ color: 'var(--text-tertiary)' }}>Nenhum aprendizado registrado. Execute planos pra LEARNER começar a aprender.</p>}
            </div>
          )}
        </div>
      </div>

      {/* ─── Modal de configuração Autopilot 24/7 ─── */}
      {autopilotProduct && autopilotConfig && (
        <div data-testid="autopilot-modal" className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.75)' }}>
          <div className="w-full max-w-md p-6" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
                <Rocket className="w-5 h-5" style={{ color: 'var(--accent-text)' }} />
              </div>
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider" style={{ fontFamily: 'Outfit, sans-serif' }}>Autopilot 24/7</h3>
                <p className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>{autopilotProduct.name}</p>
              </div>
            </div>

            <label className="flex items-center gap-3 cursor-pointer mb-4 p-3" style={{ background: 'var(--bg-base)' }}>
              <input
                type="checkbox"
                data-testid="autopilot-enabled-toggle"
                checked={autopilotConfig.autopilot_enabled}
                onChange={e => setAutopilotConfig({ ...autopilotConfig, autopilot_enabled: e.target.checked })}
              />
              <div className="flex-1">
                <p className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>Ativar operação 24/7</p>
                <p className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>JAMES roda ticks automaticamente no intervalo definido</p>
              </div>
            </label>

            <div className="mb-4">
              <label className="text-[11px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Intervalo entre ticks (minutos)</label>
              <input
                type="number" min="5" max="1440"
                data-testid="autopilot-interval-input"
                value={autopilotConfig.autopilot_interval_min}
                onChange={e => setAutopilotConfig({ ...autopilotConfig, autopilot_interval_min: parseInt(e.target.value) || 30 })}
                className="w-full mt-1 px-3 py-2 text-sm"
                style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', border: '1px solid var(--border-subtle)' }}
              />
              <p className="text-[10px] mt-1" style={{ color: 'var(--text-tertiary)' }}>Recomendado: 30 min. Min 5 min, max 24h (1440 min)</p>
            </div>

            <div className="mb-4">
              <label className="text-[11px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Auto-aprovar planos até risco</label>
              <select
                data-testid="autopilot-risk-select"
                value={autopilotConfig.auto_approve_risk}
                onChange={e => setAutopilotConfig({ ...autopilotConfig, auto_approve_risk: e.target.value })}
                className="w-full mt-1 px-3 py-2 text-sm"
                style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', border: '1px solid var(--border-subtle)' }}
              >
                <option value="none">Nenhum — só avisar (manual sempre)</option>
                <option value="low">Baixo risco (recomendado)</option>
                <option value="medium">Baixo + Médio risco</option>
                <option value="all">Todos — inclusive alto risco (arriscado!)</option>
              </select>
              <p className="text-[10px] mt-1" style={{ color: 'var(--text-tertiary)' }}>Planos acima desse risco ficam na inbox aguardando sua aprovação</p>
            </div>

            <label className="flex items-center gap-3 cursor-pointer mb-4 p-3" style={{ background: 'var(--bg-base)' }}>
              <input
                type="checkbox"
                data-testid="autopilot-daily-report-toggle"
                checked={autopilotConfig.daily_report_enabled}
                onChange={e => setAutopilotConfig({ ...autopilotConfig, daily_report_enabled: e.target.checked })}
              />
              <div className="flex-1">
                <p className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>Relatório diário via Telegram</p>
                <p className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>ECHO envia resumo automático todo dia às {autopilotConfig.daily_report_hour}h UTC</p>
              </div>
            </label>

            {autopilotConfig.daily_report_enabled && (
              <div className="mb-4">
                <label className="text-[11px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Hora do envio (UTC 0-23)</label>
                <input
                  type="number" min="0" max="23"
                  value={autopilotConfig.daily_report_hour}
                  onChange={e => setAutopilotConfig({ ...autopilotConfig, daily_report_hour: parseInt(e.target.value) || 9 })}
                  className="w-full mt-1 px-3 py-2 text-sm"
                  style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', border: '1px solid var(--border-subtle)' }}
                />
                <p className="text-[10px] mt-1" style={{ color: 'var(--text-tertiary)' }}>Brasília (UTC-3): para receber às 9h da manhã, configure 12 aqui</p>
              </div>
            )}

            {autopilotConfig.last_autopilot_tick && (
              <p className="text-[10px] mb-3" style={{ color: 'var(--text-tertiary)' }}>
                Último tick automático: {new Date(autopilotConfig.last_autopilot_tick).toLocaleString('pt-BR')}
              </p>
            )}

            <div className="flex gap-2">
              <button
                data-testid="autopilot-save-btn"
                onClick={saveAutopilot} disabled={loading}
                className="flex-1 py-2 text-xs font-bold disabled:opacity-50"
                style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}
              >
                {loading ? 'Salvando...' : 'Salvar configuração'}
              </button>
              <button
                onClick={() => setAutopilotProduct(null)}
                className="px-4 py-2 text-xs font-bold"
                style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}
              >
                Cancelar
              </button>
            </div>

            <p className="mt-4 text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
              Como funciona: o sistema verifica cada produto com Autopilot ativo a cada 60s.
              Ticks rodam no intervalo configurado. Planos dentro do risco tolerado são auto-executados.
              Os demais ficam em Planos → Validated aguardando seu clique.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
