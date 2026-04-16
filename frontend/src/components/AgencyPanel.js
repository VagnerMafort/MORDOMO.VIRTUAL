import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  X, ArrowLeft, Plus, Trash2, Package, Target, Zap, CheckCircle,
  XCircle, Clock, AlertTriangle, ChevronRight, Shield, DollarSign,
  BarChart3, Users, Play, Pause, TrendingUp
} from 'lucide-react';

function ProductCard({ product, onSelect, onDelete }) {
  const m = product.metrics || {};
  return (
    <div className="p-4 cursor-pointer transition-colors group"
      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}
      onClick={() => onSelect(product)}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
            <Package className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
          </div>
          <div>
            <p className="text-sm font-semibold">{product.name}</p>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{product.niche || product.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs px-1.5 py-0.5" style={{
            background: product.status === 'active' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
            color: product.status === 'active' ? 'var(--success)' : 'var(--error)',
          }}>{product.status === 'active' ? 'Ativo' : 'Pausado'}</span>
          <button onClick={e => { e.stopPropagation(); onDelete(product.id); }}
            className="p-1 opacity-0 group-hover:opacity-100" style={{ color: 'var(--text-tertiary)' }}>
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: 'Gasto', value: `R$${(m.spend || 0).toFixed(0)}` },
          { label: 'Receita', value: `R$${(m.revenue || 0).toFixed(0)}` },
          { label: 'ROAS', value: `${(m.roas || 0).toFixed(1)}x` },
          { label: 'Conv.', value: m.conversions || 0 },
        ].map((s, i) => (
          <div key={i} className="text-center p-1.5" style={{ background: 'var(--bg-base)' }}>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{s.label}</p>
            <p className="text-sm font-mono font-medium">{s.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function RuleCard({ rule, onToggle, onDelete }) {
  return (
    <div className="p-3 flex items-start gap-3"
      style={{
        background: rule.active ? 'rgba(255,214,0,0.03)' : 'var(--bg-elevated)',
        border: `1px solid ${rule.active ? 'rgba(255,214,0,0.2)' : 'var(--border-subtle)'}`,
      }}>
      <div className="w-7 h-7 flex-shrink-0 flex items-center justify-center"
        style={{ background: rule.active ? 'var(--accent)' : 'var(--bg-base)', border: rule.active ? 'none' : '1px solid var(--border-subtle)' }}>
        <Zap className="w-3.5 h-3.5" style={{ color: rule.active ? 'var(--accent-text)' : 'var(--text-tertiary)' }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <p className="text-sm font-medium truncate">{rule.name}</p>
          {rule.requires_approval && (
            <span className="text-xs px-1 py-0.5" style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--info)' }}>Aprovacao</span>
          )}
        </div>
        <div className="flex flex-wrap gap-1 mb-1">
          {(rule.conditions || []).map((c, i) => (
            <span key={i} className="text-xs font-mono px-1.5 py-0.5" style={{ background: 'var(--bg-base)', color: 'var(--text-secondary)' }}>
              {c.metric} {c.operator} {c.value}
            </span>
          ))}
        </div>
        <div className="flex flex-wrap gap-1">
          {(rule.actions || []).map((a, i) => (
            <span key={i} className="text-xs px-1.5 py-0.5" style={{ background: 'rgba(255,214,0,0.1)', color: 'var(--accent)' }}>
              {a.type.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-1">
        <button onClick={() => onToggle(rule.id)} className="p-1.5"
          style={{ color: rule.active ? 'var(--success)' : 'var(--text-tertiary)' }}>
          {rule.active ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
        </button>
        <button onClick={() => onDelete(rule.id)} className="p-1.5" style={{ color: 'var(--text-tertiary)' }}>
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

function ApprovalCard({ approval, onApprove, onReject }) {
  return (
    <div className="p-3 flex items-start gap-3"
      style={{ background: 'var(--bg-elevated)', border: '1px solid rgba(59,130,246,0.3)' }}>
      <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: 'var(--accent)' }} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{approval.rule_name || 'Acao pendente'}</p>
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>{approval.description}</p>
        <p className="text-xs mt-1 font-mono" style={{ color: 'var(--text-tertiary)' }}>
          {new Date(approval.created_at).toLocaleString('pt-BR')}
        </p>
      </div>
      {approval.status === 'pending' && (
        <div className="flex gap-1">
          <button onClick={() => onApprove(approval.id)} className="p-1.5"
            style={{ background: 'var(--success)', color: 'white' }}>
            <CheckCircle className="w-4 h-4" />
          </button>
          <button onClick={() => onReject(approval.id)} className="p-1.5"
            style={{ background: 'var(--error)', color: 'white' }}>
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}
      {approval.status !== 'pending' && (
        <span className="text-xs px-1.5 py-0.5" style={{
          background: approval.status === 'approved' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
          color: approval.status === 'approved' ? 'var(--success)' : 'var(--error)',
        }}>{approval.status === 'approved' ? 'Aprovado' : 'Rejeitado'}</span>
      )}
    </div>
  );
}

export default function AgencyPanel({ onClose, agentName }) {
  const { api } = useAuth();
  const [tab, setTab] = useState('products');
  const [products, setProducts] = useState([]);
  const [rules, setRules] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [accessList, setAccessList] = useState([]);
  const [showNewProduct, setShowNewProduct] = useState(false);
  const [showNewRule, setShowNewRule] = useState(false);
  const [showGrantAccess, setShowGrantAccess] = useState(false);
  const [newProduct, setNewProduct] = useState({ name: '', niche: '', target_audience: '', monthly_budget: 0 });
  const [newRule, setNewRule] = useState({ name: '', product_id: '', conditions: [{ metric: 'cpa', operator: 'gt', value: 0, period: '24h' }], actions: [{ type: 'pause_campaign', params: {} }], requires_approval: true, logic: 'AND' });
  const [grantEmail, setGrantEmail] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    loadData();
  }, [api]);

  const loadData = async () => {
    try {
      const [prods, rls, apprvls, access] = await Promise.all([
        api.get('/agency/products').catch(() => ({ data: [] })),
        api.get('/agency/rules').catch(() => ({ data: [] })),
        api.get('/agency/approvals').catch(() => ({ data: [] })),
        api.get('/agency/access/check').catch(() => ({ data: { role: 'member' } })),
      ]);
      setProducts(prods.data);
      setRules(rls.data);
      setApprovals(apprvls.data);
      setIsAdmin(access.data.role === 'admin');
      if (access.data.role === 'admin') {
        const al = await api.get('/agency/access/list').catch(() => ({ data: [] }));
        setAccessList(al.data);
      }
    } catch (e) { console.error(e); }
  };

  const createProduct = async () => {
    if (!newProduct.name.trim()) return;
    try {
      await api.post('/agency/products', newProduct);
      setShowNewProduct(false);
      setNewProduct({ name: '', niche: '', target_audience: '', monthly_budget: 0 });
      loadData();
    } catch (e) { console.error(e); }
  };

  const deleteProduct = async (id) => { await api.delete(`/agency/products/${id}`); loadData(); };
  const deleteRule = async (id) => { await api.delete(`/agency/rules/${id}`); loadData(); };
  const toggleRule = async (id) => { await api.put(`/agency/rules/${id}/toggle`); loadData(); };
  const approveAction = async (id) => { await api.post(`/agency/approvals/${id}/approve`); loadData(); };
  const rejectAction = async (id) => { await api.post(`/agency/approvals/${id}/reject`); loadData(); };

  const createRule = async () => {
    if (!newRule.name.trim() || !newRule.product_id) return;
    try {
      await api.post('/agency/rules', newRule);
      setShowNewRule(false);
      setNewRule({ name: '', product_id: '', conditions: [{ metric: 'cpa', operator: 'gt', value: 0, period: '24h' }], actions: [{ type: 'pause_campaign', params: {} }], requires_approval: true, logic: 'AND' });
      loadData();
    } catch (e) { console.error(e); }
  };

  const grantAccess = async () => {
    if (!grantEmail.trim()) return;
    try {
      await api.post('/agency/access/grant', { user_email: grantEmail, granted: true });
      setGrantEmail('');
      setShowGrantAccess(false);
      loadData();
    } catch (e) { console.error(e); }
  };

  const agencyName = `${agentName || 'Mordomo Virtual'} Agency`;
  const pendingCount = approvals.filter(a => a.status === 'pending').length;

  const tabs = [
    { id: 'products', label: 'Produtos', icon: Package },
    { id: 'rules', label: 'Regras', icon: Zap },
    { id: 'approvals', label: `Aprovacoes${pendingCount ? ` (${pendingCount})` : ''}`, icon: Shield },
    ...(isAdmin ? [{ id: 'access', label: 'Acesso', icon: Users }] : []),
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div data-testid="agency-panel" className="w-full max-w-3xl animate-fade-in max-h-[90vh] flex flex-col"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        {/* Header */}
        <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="p-1.5" style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <h2 className="text-lg font-bold tracking-tight" style={{ fontFamily: 'Outfit' }}>{agencyName}</h2>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                {products.length} produtos &middot; {rules.filter(r => r.active).length} regras ativas &middot; {pendingCount} aprovacoes pendentes
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{ color: 'var(--text-tertiary)' }}><X className="w-5 h-5" /></button>
        </div>

        {/* Tabs */}
        <div className="flex" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          {tabs.map(t => (
            <button key={t.id} data-testid={`agency-tab-${t.id}`} onClick={() => setTab(t.id)}
              className="flex-1 py-3 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
              style={{ color: tab === t.id ? 'var(--accent)' : 'var(--text-tertiary)', borderBottom: tab === t.id ? '2px solid var(--accent)' : '2px solid transparent' }}>
              <t.icon className="w-3.5 h-3.5" /> {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {tab === 'products' && (
            <div className="flex flex-col gap-3">
              <button data-testid="new-product-btn" onClick={() => setShowNewProduct(!showNewProduct)}
                className="w-full py-2.5 text-sm font-medium flex items-center justify-center gap-2"
                style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
                <Plus className="w-4 h-4" /> Novo Produto
              </button>
              {showNewProduct && (
                <div className="p-4 flex flex-col gap-3" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                  <input value={newProduct.name} onChange={e => setNewProduct({ ...newProduct, name: e.target.value })}
                    placeholder="Nome do produto" className="w-full py-2 px-3 text-sm outline-none"
                    style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                  <div className="grid grid-cols-2 gap-2">
                    <input value={newProduct.niche} onChange={e => setNewProduct({ ...newProduct, niche: e.target.value })}
                      placeholder="Nicho" className="w-full py-2 px-3 text-sm outline-none"
                      style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                    <input value={newProduct.target_audience} onChange={e => setNewProduct({ ...newProduct, target_audience: e.target.value })}
                      placeholder="Publico-alvo" className="w-full py-2 px-3 text-sm outline-none"
                      style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                  </div>
                  <input type="number" value={newProduct.monthly_budget} onChange={e => setNewProduct({ ...newProduct, monthly_budget: parseFloat(e.target.value) || 0 })}
                    placeholder="Orcamento mensal (R$)" className="w-full py-2 px-3 text-sm outline-none"
                    style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                  <button onClick={createProduct} className="py-2 text-sm font-medium"
                    style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>Criar Produto</button>
                </div>
              )}
              {products.length === 0 && !showNewProduct && (
                <p className="text-xs text-center py-6" style={{ color: 'var(--text-tertiary)' }}>Nenhum produto cadastrado.</p>
              )}
              {products.map(p => <ProductCard key={p.id} product={p} onSelect={() => {}} onDelete={deleteProduct} />)}
            </div>
          )}

          {tab === 'rules' && (
            <div className="flex flex-col gap-3">
              <button data-testid="new-rule-btn" onClick={() => setShowNewRule(!showNewRule)}
                className="w-full py-2.5 text-sm font-medium flex items-center justify-center gap-2"
                style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
                <Plus className="w-4 h-4" /> Nova Regra
              </button>
              {showNewRule && (
                <div className="p-4 flex flex-col gap-3" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                  <input value={newRule.name} onChange={e => setNewRule({ ...newRule, name: e.target.value })}
                    placeholder="Nome da regra (ex: Pausar se CPA alto)" className="w-full py-2 px-3 text-sm outline-none"
                    style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                  <select value={newRule.product_id} onChange={e => setNewRule({ ...newRule, product_id: e.target.value })}
                    className="w-full py-2 px-3 text-sm outline-none"
                    style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
                    <option value="">Selecione o produto</option>
                    {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                  <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Condicao:</p>
                  <div className="grid grid-cols-3 gap-2">
                    <select value={newRule.conditions[0]?.metric} onChange={e => setNewRule({ ...newRule, conditions: [{ ...newRule.conditions[0], metric: e.target.value }] })}
                      className="py-2 px-2 text-xs outline-none" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
                      {['cpa', 'cpc', 'ctr', 'roas', 'conversions', 'spend', 'revenue'].map(m => <option key={m} value={m}>{m.toUpperCase()}</option>)}
                    </select>
                    <select value={newRule.conditions[0]?.operator} onChange={e => setNewRule({ ...newRule, conditions: [{ ...newRule.conditions[0], operator: e.target.value }] })}
                      className="py-2 px-2 text-xs outline-none" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
                      <option value="gt">Maior que</option><option value="lt">Menor que</option>
                      <option value="gte">Maior ou igual</option><option value="lte">Menor ou igual</option>
                      <option value="change_pct_gt">Subiu mais de %</option><option value="change_pct_lt">Caiu mais de %</option>
                    </select>
                    <input type="number" value={newRule.conditions[0]?.value} onChange={e => setNewRule({ ...newRule, conditions: [{ ...newRule.conditions[0], value: parseFloat(e.target.value) || 0 }] })}
                      placeholder="Valor" className="py-2 px-2 text-xs outline-none"
                      style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                  </div>
                  <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Acao:</p>
                  <select value={newRule.actions[0]?.type} onChange={e => setNewRule({ ...newRule, actions: [{ type: e.target.value, params: {} }] })}
                    className="py-2 px-3 text-sm outline-none" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
                    <option value="pause_campaign">Pausar campanha</option>
                    <option value="scale_budget">Escalar orcamento</option>
                    <option value="reduce_budget">Reduzir orcamento</option>
                    <option value="alert">Enviar alerta</option>
                    <option value="create_report">Gerar relatorio</option>
                  </select>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={newRule.requires_approval}
                      onChange={e => setNewRule({ ...newRule, requires_approval: e.target.checked })} />
                    <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Requer aprovacao humana antes de executar</span>
                  </label>
                  <button onClick={createRule} className="py-2 text-sm font-medium"
                    style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>Criar Regra</button>
                </div>
              )}
              {rules.length === 0 && !showNewRule && (
                <p className="text-xs text-center py-6" style={{ color: 'var(--text-tertiary)' }}>Nenhuma regra criada.</p>
              )}
              {rules.map(r => <RuleCard key={r.id} rule={r} onToggle={toggleRule} onDelete={deleteRule} />)}
            </div>
          )}

          {tab === 'approvals' && (
            <div className="flex flex-col gap-3">
              {approvals.length === 0 && <p className="text-xs text-center py-6" style={{ color: 'var(--text-tertiary)' }}>Nenhuma aprovacao pendente.</p>}
              {approvals.map(a => <ApprovalCard key={a.id} approval={a} onApprove={approveAction} onReject={rejectAction} />)}
            </div>
          )}

          {tab === 'access' && isAdmin && (
            <div className="flex flex-col gap-3">
              <button onClick={() => setShowGrantAccess(!showGrantAccess)}
                className="w-full py-2.5 text-sm font-medium flex items-center justify-center gap-2"
                style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
                <Plus className="w-4 h-4" /> Conceder Acesso
              </button>
              {showGrantAccess && (
                <div className="p-4 flex gap-2" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                  <input value={grantEmail} onChange={e => setGrantEmail(e.target.value)}
                    placeholder="E-mail do usuario" className="flex-1 py-2 px-3 text-sm outline-none"
                    style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                  <button onClick={grantAccess} className="px-4 py-2 text-sm font-medium"
                    style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>Conceder</button>
                </div>
              )}
              {accessList.map(a => (
                <div key={a.user_id} className="p-3 flex items-center justify-between"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                  <div>
                    <p className="text-sm">{a.email}</p>
                    <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      Acesso {a.granted ? 'concedido' : 'revogado'} em {new Date(a.granted_at).toLocaleDateString('pt-BR')}
                    </p>
                  </div>
                  <span className="text-xs px-1.5 py-0.5" style={{
                    background: a.granted ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                    color: a.granted ? 'var(--success)' : 'var(--error)',
                  }}>{a.granted ? 'Ativo' : 'Revogado'}</span>
                </div>
              ))}
              <div className="p-3" style={{ background: 'var(--terminal-bg)', border: '1px solid var(--border-subtle)' }}>
                <p className="text-xs font-mono" style={{ color: 'var(--terminal-text)' }}>
                  Apenas o administrador pode ver e gerenciar a agencia. Conceda acesso a outros usuarios pelo e-mail cadastrado.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
