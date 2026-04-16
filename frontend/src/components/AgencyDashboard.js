import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell, Legend
} from 'recharts';
import {
  X, ArrowLeft, TrendingUp, DollarSign, Users, BarChart3,
  RefreshCw, Plug, Unlink, Link, Activity, CheckCircle, XCircle, Clock
} from 'lucide-react';

const COLORS = ['#FFD600', '#00C8FF', '#22C55E', '#EF4444', '#A855F7', '#F97316'];

function MetricCard({ label, value, prefix = '', suffix = '', color }) {
  return (
    <div className="p-3 text-center" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
      <p className="text-xs mb-1" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
      <p className="text-lg font-bold font-mono" style={{ color: color || 'var(--text-primary)' }}>
        {prefix}{typeof value === 'number' ? value.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) : value}{suffix}
      </p>
    </div>
  );
}

function IntegrationCard({ platform, integration, onConnect, onDisconnect, onSync }) {
  const [token, setToken] = useState('');
  const [accountId, setAccountId] = useState('');
  const [show, setShow] = useState(false);
  const connected = !!integration;

  const labels = { meta: 'Meta Ads (Facebook/Instagram)', google: 'Google Ads', tiktok: 'TikTok Ads' };
  const colors = { meta: '#1877F2', google: '#4285F4', tiktok: '#010101' };

  return (
    <div className="p-3" style={{ background: connected ? 'rgba(34,197,94,0.05)' : 'var(--bg-elevated)', border: `1px solid ${connected ? 'rgba(34,197,94,0.3)' : 'var(--border-subtle)'}` }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 flex items-center justify-center" style={{ background: colors[platform] || '#333' }}>
            <Plug className="w-3.5 h-3.5 text-white" />
          </div>
          <div>
            <p className="text-sm font-medium">{labels[platform] || platform}</p>
            {connected && <p className="text-xs" style={{ color: 'var(--success)' }}>Conectado: {integration.account_name}</p>}
          </div>
        </div>
        {connected ? (
          <div className="flex gap-1">
            <button onClick={() => onSync(platform)} className="p-1.5" style={{ color: 'var(--info)' }} title="Sincronizar">
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <button onClick={() => onDisconnect(platform)} className="p-1.5" style={{ color: 'var(--error)' }} title="Desconectar">
              <Unlink className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <button onClick={() => setShow(!show)} className="p-1.5" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
            <Link className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
      {show && !connected && (
        <div className="mt-3 flex flex-col gap-2">
          <input value={token} onChange={e => setToken(e.target.value)} placeholder="Access Token"
            type="password" className="w-full py-2 px-3 text-xs outline-none font-mono"
            style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
          {platform === 'meta' && (
            <input value={accountId} onChange={e => setAccountId(e.target.value)} placeholder="Account ID (ex: 123456789)"
              className="w-full py-2 px-3 text-xs outline-none font-mono"
              style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
          )}
          <button onClick={() => { onConnect(platform, { access_token: token, account_id: accountId }); setShow(false); }}
            className="py-2 text-xs font-medium" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
            Conectar
          </button>
        </div>
      )}
    </div>
  );
}

export default function AgencyDashboard({ onClose, agentName }) {
  const { api } = useAuth();
  const [tab, setTab] = useState('overview');
  const [report, setReport] = useState(null);
  const [integrations, setIntegrations] = useState([]);
  const [agentComms, setAgentComms] = useState([]);
  const [execLog, setExecLog] = useState([]);
  const [metricsHistory, setMetricsHistory] = useState({});
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [rep, intg, comms, logs] = await Promise.all([
        api.get('/agency/reports/agency').catch(() => ({ data: null })),
        api.get('/agency/integrations').catch(() => ({ data: [] })),
        api.get('/agent-comms').catch(() => ({ data: [] })),
        api.get('/agency/execution-log').catch(() => ({ data: [] })),
      ]);
      setReport(rep.data);
      setIntegrations(intg.data);
      setAgentComms(comms.data);
      setExecLog(logs.data);
      // Load metrics history for each product
      if (rep.data?.products) {
        const histMap = {};
        for (const prod of rep.data.products) {
          try {
            const h = await api.get(`/agency/metrics/${prod.id}/history`);
            histMap[prod.id] = (h.data || []).map(d => ({
              ...d.metrics,
              time: new Date(d.timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
              date: new Date(d.timestamp).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }),
            }));
          } catch {}
        }
        setMetricsHistory(histMap);
        if (rep.data.products.length > 0 && !selectedProduct) {
          setSelectedProduct(rep.data.products[0].id);
        }
      }
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const connectPlatform = async (platform, creds) => {
    try {
      await api.post('/agency/integrations/connect', { platform, credentials: creds });
      loadAll();
    } catch (e) { alert(e.response?.data?.detail || 'Erro'); }
  };
  const disconnectPlatform = async (platform) => { await api.delete(`/agency/integrations/${platform}`); loadAll(); };
  const syncPlatform = async (platform) => {
    try { await api.post(`/agency/integrations/${platform}/sync`); loadAll(); } catch (e) { console.error(e); }
  };

  const agencyName = `${agentName || 'Mordomo Virtual'} Agency`;
  const products = report?.products || [];
  const pieData = products.map((p, i) => ({ name: p.name, value: p.metrics?.spend || 0 })).filter(d => d.value > 0);

  const tabs = [
    { id: 'overview', label: 'Visao Geral' },
    { id: 'timeline', label: 'Timeline' },
    { id: 'executions', label: `Execucoes (${execLog.length})` },
    { id: 'integrations', label: 'Integracoes' },
    { id: 'agents', label: 'Agentes' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div data-testid="agency-dashboard" className="w-full max-w-4xl animate-fade-in max-h-[90vh] flex flex-col"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="p-1.5" style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <h2 className="text-lg font-bold" style={{ fontFamily: 'Outfit' }}>{agencyName} - Dashboard</h2>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Metricas, integracoes e comunicacao entre agentes</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={loadAll} className="p-1.5" style={{ color: 'var(--text-tertiary)' }}><RefreshCw className="w-4 h-4" /></button>
            <button onClick={onClose} style={{ color: 'var(--text-tertiary)' }}><X className="w-5 h-5" /></button>
          </div>
        </div>

        <div className="flex" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className="flex-1 py-3 text-xs font-medium transition-colors"
              style={{ color: tab === t.id ? 'var(--accent)' : 'var(--text-tertiary)', borderBottom: tab === t.id ? '2px solid var(--accent)' : '2px solid transparent' }}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {tab === 'overview' && report && (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <MetricCard label="Gasto Total" value={report.total_spend} prefix="R$" color="var(--error)" />
                <MetricCard label="Receita Total" value={report.total_revenue} prefix="R$" color="var(--success)" />
                <MetricCard label="ROAS" value={report.overall_roas} suffix="x" color="var(--accent)" />
                <MetricCard label="Conversoes" value={report.total_conversions} color="var(--info)" />
              </div>

              {products.length > 0 && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Spend by product */}
                  <div className="p-4" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                    <p className="text-xs font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>Gasto por Produto</p>
                    <div style={{ height: 200 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={products}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="name" tick={{ fill: '#71717A', fontSize: 10 }} />
                          <YAxis tick={{ fill: '#71717A', fontSize: 10 }} />
                          <Tooltip contentStyle={{ background: '#1A1A1A', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 12 }} />
                          <Bar dataKey="metrics.spend" name="Gasto" fill="#FFD600" />
                          <Bar dataKey="metrics.revenue" name="Receita" fill="#22C55E" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {pieData.length > 0 && (
                    <div className="p-4" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                      <p className="text-xs font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>Distribuicao de Investimento</p>
                      <div style={{ height: 200 }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name }) => name}>
                              {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                            </Pie>
                            <Tooltip contentStyle={{ background: '#1A1A1A', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 12 }} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                <div className="p-3 text-center" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Regras Ativas</p>
                  <p className="text-xl font-bold" style={{ color: 'var(--accent)' }}>{report.active_rules}</p>
                </div>
                <div className="p-3 text-center" style={{ background: report.pending_approvals > 0 ? 'rgba(255,214,0,0.05)' : 'var(--bg-elevated)', border: `1px solid ${report.pending_approvals > 0 ? 'rgba(255,214,0,0.3)' : 'var(--border-subtle)'}` }}>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Aprovacoes Pendentes</p>
                  <p className="text-xl font-bold" style={{ color: report.pending_approvals > 0 ? 'var(--accent)' : 'var(--text-primary)' }}>{report.pending_approvals}</p>
                </div>
              </div>
            </div>
          )}

          {tab === 'timeline' && (
            <div className="flex flex-col gap-4">
              {/* Product selector */}
              {products.length > 0 && (
                <select value={selectedProduct || ''} onChange={e => setSelectedProduct(e.target.value)}
                  className="py-2 px-3 text-sm outline-none"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
                  {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              )}

              {/* Line chart - Spend & Revenue over time */}
              {selectedProduct && (metricsHistory[selectedProduct] || []).length > 0 ? (
                <>
                  <div className="p-4" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                    <p className="text-xs font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>Gasto vs Receita (Timeline)</p>
                    <div style={{ height: 250 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={metricsHistory[selectedProduct]}>
                          <defs>
                            <linearGradient id="gradSpend" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
                              <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="gradRevenue" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#22C55E" stopOpacity={0.3} />
                              <stop offset="95%" stopColor="#22C55E" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="time" tick={{ fill: '#71717A', fontSize: 10 }} />
                          <YAxis tick={{ fill: '#71717A', fontSize: 10 }} />
                          <Tooltip contentStyle={{ background: '#1A1A1A', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 12 }} />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Area type="monotone" dataKey="spend" name="Gasto" stroke="#EF4444" fill="url(#gradSpend)" strokeWidth={2} />
                          <Area type="monotone" dataKey="revenue" name="Receita" stroke="#22C55E" fill="url(#gradRevenue)" strokeWidth={2} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="p-4" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                    <p className="text-xs font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>ROAS e CPA (Timeline)</p>
                    <div style={{ height: 200 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={metricsHistory[selectedProduct]}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="time" tick={{ fill: '#71717A', fontSize: 10 }} />
                          <YAxis tick={{ fill: '#71717A', fontSize: 10 }} />
                          <Tooltip contentStyle={{ background: '#1A1A1A', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 12 }} />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Line type="monotone" dataKey="roas" name="ROAS" stroke="#FFD600" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="cpa" name="CPA" stroke="#A855F7" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="ctr" name="CTR" stroke="#00C8FF" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-8">
                  <Activity className="w-8 h-8 mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
                  <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Sem dados historicos ainda.</p>
                  <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
                    Atualize as metricas do produto ou conecte uma plataforma para comecar a coletar dados.
                  </p>
                </div>
              )}
            </div>
          )}

          {tab === 'executions' && (
            <div className="flex flex-col gap-2">
              <p className="text-xs mb-2" style={{ color: 'var(--text-secondary)' }}>
                Historico de acoes executadas pelo motor de regras e aprovacoes:
              </p>
              {execLog.length === 0 && (
                <p className="text-xs text-center py-6" style={{ color: 'var(--text-tertiary)' }}>Nenhuma execucao registrada.</p>
              )}
              {execLog.map(log => (
                <div key={log.id} className="p-3"
                  style={{ background: 'var(--bg-elevated)', border: `1px solid ${log.result?.success ? 'rgba(34,197,94,0.2)' : 'var(--border-subtle)'}` }}>
                  <div className="flex items-center gap-2 mb-1">
                    {log.result?.success ? (
                      <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} />
                    ) : (
                      <XCircle className="w-4 h-4" style={{ color: 'var(--error)' }} />
                    )}
                    <p className="text-sm font-medium">{log.rule_name || log.action?.type || 'Acao'}</p>
                    <span className="text-xs ml-auto" style={{ color: 'var(--text-tertiary)' }}>
                      {new Date(log.executed_at).toLocaleString('pt-BR')}
                    </span>
                  </div>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {log.result?.details || JSON.stringify(log.action).slice(0, 100)}
                  </p>
                  {log.result?.platform_result && (
                    <p className="text-xs font-mono mt-1" style={{ color: 'var(--info)' }}>
                      Plataforma: {log.result.platform_result.executed ? 'Executado' : 'Nao executado'} - {log.result.platform_result.reason || log.result.platform_result.note || ''}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === 'integrations' && (
            <div className="flex flex-col gap-3">
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Conecte suas contas de ads para sincronizar metricas automaticamente.
              </p>
              {['meta', 'google', 'tiktok'].map(p => (
                <IntegrationCard key={p} platform={p}
                  integration={integrations.find(i => i.platform === p)}
                  onConnect={connectPlatform} onDisconnect={disconnectPlatform} onSync={syncPlatform} />
              ))}
              <div className="p-3" style={{ background: 'var(--terminal-bg)', border: '1px solid var(--border-subtle)' }}>
                <p className="text-xs font-mono" style={{ color: 'var(--terminal-text)' }}>
                  As credenciais sao armazenadas de forma segura por usuario. Cada usuario conecta suas proprias contas.
                </p>
              </div>
            </div>
          )}

          {tab === 'agents' && (
            <div className="flex flex-col gap-3">
              <p className="text-xs mb-2" style={{ color: 'var(--text-secondary)' }}>
                Comunicacao entre agentes - mensagens trocadas pelo sistema:
              </p>
              {agentComms.length === 0 && (
                <p className="text-xs text-center py-6" style={{ color: 'var(--text-tertiary)' }}>
                  Nenhuma comunicacao entre agentes registrada. As mensagens aparecem quando regras sao disparadas.
                </p>
              )}
              {agentComms.map(msg => (
                <div key={msg.id} className="p-3"
                  style={{ background: 'var(--bg-elevated)', border: `1px solid ${msg.status === 'pending' ? 'rgba(255,214,0,0.2)' : 'var(--border-subtle)'}` }}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono px-1.5 py-0.5" style={{ background: 'rgba(255,214,0,0.1)', color: 'var(--accent)' }}>
                      {msg.from_agent}
                    </span>
                    <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>→</span>
                    <span className="text-xs font-mono px-1.5 py-0.5" style={{ background: 'rgba(0,200,255,0.1)', color: 'var(--info)' }}>
                      {msg.to_agent}
                    </span>
                    <span className="text-xs ml-auto" style={{ color: 'var(--text-tertiary)' }}>
                      {msg.message_type}
                    </span>
                  </div>
                  <p className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                    {JSON.stringify(msg.payload || {}).slice(0, 150)}
                  </p>
                  <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
                    {new Date(msg.created_at).toLocaleString('pt-BR')} &middot; {msg.status}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
