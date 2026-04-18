import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  X, LayoutDashboard, Users, Shield, Activity, FileText, Monitor, Cpu,
  UserPlus, Lock, Unlock, Trash2, KeyRound, RefreshCw, Gauge, Circle, Copy, Plug
} from 'lucide-react';
import { toast } from 'sonner';

const TABS = [
  { id: 'dashboard', label: 'Dashboard', Icon: LayoutDashboard },
  { id: 'users', label: 'Usuários', Icon: Users },
  { id: 'modules', label: 'Módulos', Icon: Shield },
  { id: 'integrations', label: 'Integrações', Icon: Plug },
  { id: 'usage', label: 'Uso', Icon: Gauge },
  { id: 'logs', label: 'Logs', Icon: FileText },
  { id: 'sessions', label: 'Sessões', Icon: Monitor },
  { id: 'alerts', label: 'Alertas', Icon: Activity },
  { id: 'system', label: 'Sistema', Icon: Cpu },
];

export default function AdminPanel({ onClose }) {
  const { api } = useAuth();
  const [tab, setTab] = useState('dashboard');

  return (
    <div data-testid="admin-panel" className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}>
      <div className="w-full max-w-6xl h-full max-h-[92vh] flex flex-col overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b" style={{ borderColor: 'var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
              <Shield className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
            </div>
            <h2 className="text-sm font-bold tracking-wider uppercase" style={{ fontFamily: 'Outfit, sans-serif' }}>Painel Administrativo</h2>
          </div>
          <button data-testid="admin-close-btn" onClick={onClose} className="p-1.5 transition-colors" style={{ color: 'var(--text-tertiary)' }}>
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex overflow-x-auto border-b" style={{ borderColor: 'var(--border-subtle)' }}>
          {TABS.map(t => {
            const Icon = t.Icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                data-testid={`admin-tab-${t.id}`}
                onClick={() => setTab(t.id)}
                className="px-4 py-3 text-xs font-semibold flex items-center gap-2 whitespace-nowrap transition-colors"
                style={{
                  color: active ? 'var(--accent)' : 'var(--text-secondary)',
                  borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
                  background: active ? 'rgba(255,214,0,0.04)' : 'transparent'
                }}
              >
                <Icon className="w-3.5 h-3.5" /> {t.label}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5" style={{ background: 'var(--bg-base)' }}>
          {tab === 'dashboard' && <DashboardTab api={api} />}
          {tab === 'users' && <UsersTab api={api} />}
          {tab === 'modules' && <ModulesTab api={api} />}
          {tab === 'integrations' && <IntegrationsTab api={api} />}
          {tab === 'usage' && <UsageTab api={api} />}
          {tab === 'logs' && <LogsTab api={api} />}
          {tab === 'sessions' && <SessionsTab api={api} />}
          {tab === 'alerts' && <AlertsTab api={api} />}
          {tab === 'system' && <SystemTab api={api} />}
        </div>
      </div>
    </div>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
function DashboardTab({ api }) {
  const [data, setData] = useState(null);
  const load = useCallback(async () => {
    try { const { data } = await api.get('/admin/dashboard'); setData(data); } catch {}
  }, [api]);
  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t); }, [load]);

  if (!data) return <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Carregando...</p>;

  return (
    <div className="space-y-5">
      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Kpi label="Usuários totais" value={data.users.total} testid="kpi-users-total" />
        <Kpi label="Online agora" value={data.users.online} testid="kpi-users-online" accent />
        <Kpi label="Mensagens hoje" value={data.today.messages} testid="kpi-msgs-today" />
        <Kpi label="Admins" value={data.users.admins} testid="kpi-admins" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="p-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
          <h3 className="text-xs font-bold tracking-wider uppercase mb-3" style={{ color: 'var(--text-secondary)' }}>RAM</h3>
          <BarLine percent={data.system.ram_percent} used={`${data.system.ram_used_mb} MB`} total={`${data.system.ram_total_mb} MB`} />
        </div>
        <div className="p-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
          <h3 className="text-xs font-bold tracking-wider uppercase mb-3" style={{ color: 'var(--text-secondary)' }}>Disco</h3>
          <BarLine percent={data.system.disk_percent} used={`${data.system.disk_used_gb} GB`} total={`${data.system.disk_total_gb} GB`} />
        </div>
      </div>
    </div>
  );
}

function Kpi({ label, value, testid, accent }) {
  return (
    <div data-testid={testid} className="p-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
      <p className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
      <p className="text-2xl font-bold" style={{ color: accent ? 'var(--accent)' : 'var(--text-primary)', fontFamily: 'Outfit, sans-serif' }}>{value}</p>
    </div>
  );
}

function BarLine({ percent, used, total }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>
        <span>{used} / {total}</span>
        <span className="font-bold" style={{ color: 'var(--accent)' }}>{percent}%</span>
      </div>
      <div className="h-2" style={{ background: 'var(--bg-base)' }}>
        <div className="h-full transition-all" style={{ width: `${Math.min(100, percent)}%`, background: percent > 80 ? 'var(--error)' : 'var(--accent)' }} />
      </div>
    </div>
  );
}

// ─── Users ────────────────────────────────────────────────────────────────────
function UsersTab({ api }) {
  const [users, setUsers] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState(null);
  const [resetting, setResetting] = useState(null);
  const [modules, setModules] = useState([]);

  const load = useCallback(async () => {
    try {
      const [u, m] = await Promise.all([api.get('/admin/users'), api.get('/admin/modules')]);
      setUsers(u.data); setModules(m.data);
    } catch (e) { console.error(e); }
  }, [api]);
  useEffect(() => { load(); }, [load]);

  const toggleBlock = async (u) => {
    await api.put(`/admin/users/${u.id}`, { blocked: !u.blocked });
    load();
  };
  const del = async (u) => {
    if (!window.confirm(`Excluir usuário ${u.email}?`)) return;
    await api.delete(`/admin/users/${u.id}`);
    load();
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center">
        <h3 className="text-xs font-bold tracking-wider uppercase" style={{ color: 'var(--text-secondary)' }}>Usuários ({users.length})</h3>
        <button data-testid="admin-create-user-btn" onClick={() => setShowCreate(true)}
          className="px-3 py-1.5 text-xs font-semibold flex items-center gap-1.5"
          style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
          <UserPlus className="w-3.5 h-3.5" /> Novo Usuário
        </button>
      </div>

      <div className="overflow-x-auto" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        <table className="w-full text-xs">
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <Th>Email</Th><Th>Nome</Th><Th>Role</Th><Th>Status</Th><Th>Último login</Th><Th>Logins</Th><Th>Ações</Th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} data-testid={`admin-user-row-${u.id}`} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <Td>{u.email}</Td>
                <Td>{u.name}</Td>
                <Td><span className="px-1.5 py-0.5" style={{ background: u.role === 'admin' ? 'var(--accent)' : 'var(--bg-elevated)', color: u.role === 'admin' ? 'var(--accent-text)' : 'var(--text-secondary)' }}>{u.role}</span></Td>
                <Td>
                  {u.blocked ? <span style={{ color: 'var(--error)' }}>Bloqueado</span> : <span style={{ color: 'var(--success)' }}>Ativo</span>}
                </Td>
                <Td>{u.last_login ? new Date(u.last_login).toLocaleString('pt-BR') : '-'}</Td>
                <Td>{u.login_count || 0}</Td>
                <Td>
                  <div className="flex gap-1">
                    <IconBtn testid={`edit-user-${u.id}`} onClick={() => setEditing(u)} title="Editar módulos/quota"><Shield className="w-3.5 h-3.5" /></IconBtn>
                    <IconBtn testid={`reset-pwd-${u.id}`} onClick={() => setResetting(u)} title="Redefinir senha"><KeyRound className="w-3.5 h-3.5" /></IconBtn>
                    <IconBtn testid={`toggle-block-${u.id}`} onClick={() => toggleBlock(u)} title={u.blocked ? 'Desbloquear' : 'Bloquear'}>
                      {u.blocked ? <Unlock className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
                    </IconBtn>
                    <IconBtn testid={`delete-user-${u.id}`} onClick={() => del(u)} title="Excluir" danger><Trash2 className="w-3.5 h-3.5" /></IconBtn>
                  </div>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && <CreateUserModal api={api} modules={modules} onClose={() => setShowCreate(false)} onDone={() => { setShowCreate(false); load(); }} />}
      {editing && <EditUserModal api={api} user={editing} modules={modules} onClose={() => setEditing(null)} onDone={() => { setEditing(null); load(); }} />}
      {resetting && <ResetPasswordModal api={api} user={resetting} onClose={() => setResetting(null)} />}
    </div>
  );
}

function Th({ children }) {
  return <th className="text-left px-3 py-2 font-semibold uppercase tracking-wider text-[10px]" style={{ color: 'var(--text-tertiary)' }}>{children}</th>;
}
function Td({ children }) {
  return <td className="px-3 py-2" style={{ color: 'var(--text-secondary)' }}>{children}</td>;
}
function IconBtn({ children, onClick, title, testid, danger }) {
  return (
    <button data-testid={testid} onClick={onClick} title={title}
      className="p-1.5 transition-colors"
      style={{ background: 'var(--bg-elevated)', color: danger ? 'var(--error)' : 'var(--text-secondary)' }}
    >{children}</button>
  );
}

function CreateUserModal({ api, modules, onClose, onDone }) {
  const [form, setForm] = useState({ email: '', password: '', name: '', role: 'user', allowed_modules: ['chat', 'handsfree', 'mentorship', 'telegram', 'agents', 'skills', 'monitor'] });
  const [err, setErr] = useState('');
  const submit = async () => {
    try {
      await api.post('/admin/users', form);
      onDone();
    } catch (e) { setErr(e.response?.data?.detail || 'Erro'); }
  };
  const toggleMod = (key) => {
    setForm(f => ({ ...f, allowed_modules: f.allowed_modules.includes(key) ? f.allowed_modules.filter(k => k !== key) : [...f.allowed_modules, key] }));
  };
  return (
    <ModalShell title="Criar Usuário" onClose={onClose}>
      <Input label="E-mail" value={form.email} onChange={v => setForm({ ...form, email: v })} testid="create-email" />
      <Input label="Nome" value={form.name} onChange={v => setForm({ ...form, name: v })} testid="create-name" />
      <Input label="Senha" type="password" value={form.password} onChange={v => setForm({ ...form, password: v })} testid="create-password" />
      <div className="mb-3">
        <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>Role</label>
        <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} className="w-full px-2 py-1.5 text-xs" data-testid="create-role"
          style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
          <option value="user">user</option>
          <option value="admin">admin</option>
        </select>
      </div>
      <ModulesCheckboxList modules={modules} selected={form.allowed_modules} onToggle={toggleMod} />
      {err && <p className="text-xs mb-2" style={{ color: 'var(--error)' }}>{err}</p>}
      <button data-testid="submit-create-user" onClick={submit} className="w-full py-2 text-xs font-bold" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
        Criar Usuário
      </button>
    </ModalShell>
  );
}

function EditUserModal({ api, user, modules, onClose, onDone }) {
  const [allowed, setAllowed] = useState(user.allowed_modules || []);
  const [quota, setQuota] = useState({
    messages_per_day: user.quota?.messages_per_day || 0,
    tasks_per_day: user.quota?.tasks_per_day || 0,
    uploads_per_day: user.quota?.uploads_per_day || 0,
  });
  const [role, setRole] = useState(user.role);
  const toggleMod = (key) => {
    setAllowed(cur => cur.includes(key) ? cur.filter(k => k !== key) : [...cur, key]);
  };
  const save = async () => {
    try {
      await api.put(`/admin/users/${user.id}`, { allowed_modules: allowed, role });
      // quota numbers
      const q = {};
      if (+quota.messages_per_day > 0) q.messages_per_day = +quota.messages_per_day;
      if (+quota.tasks_per_day > 0) q.tasks_per_day = +quota.tasks_per_day;
      if (+quota.uploads_per_day > 0) q.uploads_per_day = +quota.uploads_per_day;
      await api.put(`/admin/users/${user.id}/quota`, q);
      onDone();
    } catch (e) { alert(e.response?.data?.detail || 'Erro'); }
  };
  return (
    <ModalShell title={`Editar: ${user.email}`} onClose={onClose}>
      <div className="mb-3">
        <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>Role</label>
        <select value={role} onChange={e => setRole(e.target.value)} className="w-full px-2 py-1.5 text-xs" data-testid="edit-role"
          style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
          <option value="user">user</option>
          <option value="admin">admin</option>
        </select>
      </div>
      <h4 className="text-[10px] uppercase tracking-wider mt-3 mb-2" style={{ color: 'var(--text-tertiary)' }}>Cotas diárias (0 = sem limite)</h4>
      <div className="grid grid-cols-3 gap-2 mb-3">
        <Input small label="Msgs/dia" type="number" value={quota.messages_per_day} onChange={v => setQuota({ ...quota, messages_per_day: v })} testid="quota-msgs" />
        <Input small label="Tasks/dia" type="number" value={quota.tasks_per_day} onChange={v => setQuota({ ...quota, tasks_per_day: v })} testid="quota-tasks" />
        <Input small label="Uploads/dia" type="number" value={quota.uploads_per_day} onChange={v => setQuota({ ...quota, uploads_per_day: v })} testid="quota-uploads" />
      </div>
      <ModulesCheckboxList modules={modules} selected={allowed} onToggle={toggleMod} />
      <button data-testid="submit-edit-user" onClick={save} className="w-full py-2 text-xs font-bold" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>Salvar</button>
    </ModalShell>
  );
}

function ResetPasswordModal({ api, user, onClose }) {
  const [pwd, setPwd] = useState('');
  const [done, setDone] = useState(false);
  const submit = async () => {
    await api.post(`/admin/users/${user.id}/reset-password`, { new_password: pwd });
    setDone(true);
  };
  return (
    <ModalShell title={`Redefinir senha: ${user.email}`} onClose={onClose}>
      {done ? (
        <div>
          <p className="text-xs mb-3" style={{ color: 'var(--success)' }}>Senha alterada com sucesso. Entregue ao usuário:</p>
          <code className="block p-2 mb-3 text-xs" style={{ background: 'var(--bg-base)', color: 'var(--accent)' }}>{pwd}</code>
          <button data-testid="close-reset-modal" onClick={onClose} className="w-full py-2 text-xs font-bold" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>OK</button>
        </div>
      ) : (
        <>
          <Input label="Nova senha" type="text" value={pwd} onChange={setPwd} testid="new-password-input" />
          <button data-testid="submit-reset-pwd" onClick={submit} disabled={!pwd} className="w-full py-2 text-xs font-bold disabled:opacity-50" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>Redefinir</button>
        </>
      )}
    </ModalShell>
  );
}

function ModulesCheckboxList({ modules, selected, onToggle }) {
  return (
    <div className="mb-4">
      <label className="text-[10px] uppercase tracking-wider block mb-2" style={{ color: 'var(--text-tertiary)' }}>Módulos liberados</label>
      <div className="grid grid-cols-2 gap-1 max-h-48 overflow-y-auto p-2" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}>
        {modules.map(m => (
          <label key={m.key} data-testid={`module-checkbox-${m.key}`} className="flex items-center gap-2 text-xs cursor-pointer py-1">
            <input type="checkbox" checked={selected.includes(m.key)} onChange={() => onToggle(m.key)} />
            <span style={{ color: selected.includes(m.key) ? 'var(--text-primary)' : 'var(--text-tertiary)' }}>{m.name}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function ModalShell({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-3" style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(6px)' }}>
      <div className="w-full max-w-md max-h-[92vh] overflow-y-auto p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-bold tracking-wider uppercase" style={{ fontFamily: 'Outfit, sans-serif' }}>{title}</h3>
          <button onClick={onClose} style={{ color: 'var(--text-tertiary)' }}><X className="w-4 h-4" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Input({ label, value, onChange, type = 'text', testid, small }) {
  return (
    <div className={small ? 'mb-1' : 'mb-3'}>
      <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--text-tertiary)' }}>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} data-testid={testid}
        className="w-full px-2 py-1.5 text-xs outline-none"
        style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
    </div>
  );
}

// ─── Modules Tab ──────────────────────────────────────────────────────────────
function ModulesTab({ api }) {
  const [modules, setModules] = useState([]);
  useEffect(() => { (async () => { try { const { data } = await api.get('/admin/modules'); setModules(data); } catch {} })(); }, [api]);
  return (
    <div>
      <h3 className="text-xs font-bold tracking-wider uppercase mb-3" style={{ color: 'var(--text-secondary)' }}>Catálogo de Módulos ({modules.length})</h3>
      <p className="text-xs mb-4" style={{ color: 'var(--text-tertiary)' }}>
        Estes são todos os módulos do sistema. A liberação individual é feita em <b>Usuários → Editar</b>. Módulos em cinza ainda serão implementados em fases futuras.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {modules.map(m => (
          <div key={m.key} data-testid={`module-card-${m.key}`} className="p-3" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold" style={{ color: 'var(--accent)' }}>{m.name}</span>
              <code className="text-[10px] px-1.5 py-0.5" style={{ background: 'var(--bg-base)', color: 'var(--text-tertiary)' }}>{m.key}</code>
            </div>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{m.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Usage Tab ────────────────────────────────────────────────────────────────
function UsageTab({ api }) {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(7);
  useEffect(() => { (async () => { try { const { data } = await api.get(`/admin/usage?days=${days}`); setData(data); } catch {} })(); }, [api, days]);
  if (!data) return <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Carregando...</p>;
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold tracking-wider uppercase" style={{ color: 'var(--text-secondary)' }}>Uso — últimos {days} dias</h3>
        <select value={days} onChange={e => setDays(+e.target.value)} className="px-2 py-1 text-xs" data-testid="usage-days-select"
          style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>
          <option value={1}>1 dia</option>
          <option value={7}>7 dias</option>
          <option value={30}>30 dias</option>
        </select>
      </div>
      <div className="overflow-x-auto" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        <table className="w-full text-xs">
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <Th>Usuário</Th><Th>Mensagens</Th><Th>Tasks</Th><Th>Uploads</Th><Th>Downloads</Th>
            </tr>
          </thead>
          <tbody>
            {data.users.length === 0 && (
              <tr><td colSpan="5" className="px-3 py-6 text-center text-xs" style={{ color: 'var(--text-tertiary)' }}>Sem uso registrado no período.</td></tr>
            )}
            {data.users.map(u => (
              <tr key={u.user_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <Td>{u.email}</Td>
                <Td>{u.messages}</Td>
                <Td>{u.tasks}</Td>
                <Td>{u.uploads}</Td>
                <Td>{u.downloads}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Logs Tab ─────────────────────────────────────────────────────────────────
function LogsTab({ api }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    try { const { data } = await api.get('/admin/audit?limit=200'); setLogs(data); } catch {}
    setLoading(false);
  }, [api]);
  useEffect(() => { load(); }, [load]);
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold tracking-wider uppercase" style={{ color: 'var(--text-secondary)' }}>Audit Log ({logs.length})</h3>
        <button data-testid="reload-logs" onClick={load} className="p-1.5" style={{ background: 'var(--bg-surface)' }}><RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} style={{ color: 'var(--text-secondary)' }} /></button>
      </div>
      <div className="space-y-1">
        {logs.map(l => (
          <div key={l.id} className="p-2 flex items-start gap-3 text-xs" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
            <span className="w-32 flex-shrink-0" style={{ color: 'var(--text-tertiary)' }}>{new Date(l.created_at).toLocaleString('pt-BR')}</span>
            <span className="font-bold w-32 flex-shrink-0" style={{ color: 'var(--accent)' }}>{l.action}</span>
            <span className="flex-shrink-0" style={{ color: 'var(--text-secondary)' }}>{l.user_email || l.user_id}</span>
            <span className="truncate" style={{ color: 'var(--text-tertiary)' }}>{l.target} {l.details && Object.keys(l.details).length > 0 ? JSON.stringify(l.details) : ''}</span>
          </div>
        ))}
        {logs.length === 0 && <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Nenhum log ainda.</p>}
      </div>
    </div>
  );
}

// ─── Sessions Tab ─────────────────────────────────────────────────────────────
function SessionsTab({ api }) {
  const [data, setData] = useState(null);
  const load = useCallback(async () => {
    try { const { data } = await api.get('/admin/sessions'); setData(data); } catch {}
  }, [api]);
  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t); }, [load]);
  if (!data) return <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Carregando...</p>;
  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-xs font-bold tracking-wider uppercase mb-2" style={{ color: 'var(--success)' }}>
          <Circle className="inline w-2 h-2 mr-1 fill-current" /> Online agora ({data.online.length})
        </h3>
        <SessionsTable rows={data.online} />
      </div>
      <div>
        <h3 className="text-xs font-bold tracking-wider uppercase mb-2" style={{ color: 'var(--text-tertiary)' }}>Últimas sessões</h3>
        <SessionsTable rows={data.recent} />
      </div>
    </div>
  );
}

function SessionsTable({ rows }) {
  if (!rows.length) return <p className="text-xs px-2 py-3" style={{ color: 'var(--text-tertiary)' }}>Nenhuma sessão.</p>;
  return (
    <div className="overflow-x-auto" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
      <table className="w-full text-xs">
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <Th>Email</Th><Th>IP</Th><Th>User-Agent</Th><Th>Última atividade</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <Td>{s.email}</Td>
              <Td><code className="text-[11px]">{s.ip}</code></Td>
              <Td><span className="truncate block max-w-md">{s.user_agent}</span></Td>
              <Td>{new Date(s.last_seen).toLocaleString('pt-BR')}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── System Tab ───────────────────────────────────────────────────────────────
function SystemTab({ api }) {
  const [data, setData] = useState(null);
  const [resets, setResets] = useState([]);
  useEffect(() => { (async () => {
    try { const { data } = await api.get('/system/memory-stats'); setData(data); } catch {}
    try { const { data } = await api.get('/admin/password-resets'); setResets(data); } catch {}
  })(); }, [api]);
  const copy = (token) => { navigator.clipboard.writeText(token); alert('Token copiado'); };
  if (!data) return <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Carregando...</p>;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Kpi label="Mensagens" value={data.total_messages} testid="sys-msgs" />
        <Kpi label="Conversas" value={data.total_conversations} testid="sys-convs" />
        <Kpi label="Mentorias" value={data.total_mentorships} testid="sys-ments" />
        <Kpi label="Regras ativas" value={data.active_rules} testid="sys-rules" />
        <Kpi label="Cache" value={data.cache_entries} testid="sys-cache" />
        <Kpi label="Sumários" value={data.conversation_summaries} testid="sys-sum" />
        <Kpi label="Tasks fila" value={data.tasks_pending} testid="sys-tp" />
        <Kpi label="Tasks feitas" value={data.tasks_completed} testid="sys-tc" />
      </div>
      <div>
        <h3 className="text-xs font-bold tracking-wider uppercase mb-2" style={{ color: 'var(--text-secondary)' }}>Tokens de Recuperação de Senha ativos</h3>
        {resets.length === 0 ? (
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Nenhum token pendente. Usuários podem solicitar em "Esqueci senha" na tela de login.</p>
        ) : (
          <div className="space-y-1">
            {resets.map(r => (
              <div key={r.token} className="p-2 flex items-center gap-2 text-xs" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>{r.email}</span>
                <code className="flex-1 truncate" style={{ color: 'var(--accent)' }}>{r.token}</code>
                <button onClick={() => copy(r.token)} className="p-1" style={{ color: 'var(--text-tertiary)' }}><Copy className="w-3.5 h-3.5" /></button>
                <span style={{ color: 'var(--text-tertiary)' }}>exp: {new Date(r.expires_at).toLocaleTimeString('pt-BR')}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


// ─── Alerts Tab ───────────────────────────────────────────────────────────────
function AlertsTab({ api }) {
  const [alerts, setAlerts] = useState([]);
  const load = useCallback(async () => {
    try { const { data } = await api.get('/admin/alerts?limit=100'); setAlerts(data); } catch {}
  }, [api]);
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);

  const SEVERITY_COLORS = { critical: 'var(--error)', warning: '#fbbf24', info: 'var(--info)' };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold tracking-wider uppercase" style={{ color: 'var(--text-secondary)' }}>Alertas do Sistema ({alerts.length})</h3>
        <button data-testid="reload-alerts" onClick={load} className="p-1.5" style={{ background: 'var(--bg-surface)' }}>
          <RefreshCw className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
        </button>
      </div>
      <p className="text-[11px] mb-3" style={{ color: 'var(--text-tertiary)' }}>
        System Watchdog monitora MongoDB, Ollama, disco e RAM a cada 60 segundos.
      </p>
      <div className="space-y-1">
        {alerts.length === 0 && <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Nenhum alerta — tudo saudável ✓</p>}
        {alerts.map((a, i) => (
          <div key={i} className="p-2 flex items-start gap-3 text-xs" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
            <span className="w-20 flex-shrink-0 font-bold uppercase text-[10px]" style={{ color: SEVERITY_COLORS[a.severity] || 'var(--text-tertiary)' }}>{a.severity}</span>
            <span className="w-16 flex-shrink-0 font-bold" style={{ color: 'var(--accent)' }}>{a.kind}</span>
            <span className="flex-1" style={{ color: 'var(--text-secondary)' }}>{a.message}</span>
            <span className="w-32 flex-shrink-0 text-right" style={{ color: 'var(--text-tertiary)' }}>
              {new Date(a.created_at).toLocaleString('pt-BR')}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Integrations Tab (admin configura OAuth apps) ────────────────────────────
function IntegrationsTab({ api }) {
  return (
    <div className="space-y-4">
      <GoogleIntegrationCard api={api} />
      <MetaIntegrationCard api={api} />
      <TiktokIntegrationCard api={api} />
    </div>
  );
}

function GoogleIntegrationCard({ api }) {
  const [cfg, setCfg] = useState(null);
  const [form, setForm] = useState({ client_id: '', client_secret: '', enabled: true });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try { const { data } = await api.get('/admin/integrations/google'); setCfg(data); setForm(f => ({ ...f, client_id: data.client_id || '', enabled: data.enabled })); } catch {}
  }, [api]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      await api.put('/admin/integrations/google', form);
      toast.success('Configuração Google salva');
      setForm(f => ({ ...f, client_secret: '' }));
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro ao salvar'); }
    setSaving(false);
  };

  const remove = async () => {
    if (!window.confirm('Remover a configuração do Google? Todos os usuários conectados perderão acesso.')) return;
    await api.delete('/admin/integrations/google');
    toast.success('Configuração removida');
    load();
  };

  const copyRedirect = () => {
    const uri = `${window.location.origin}/api/oauth/google/callback`;
    navigator.clipboard.writeText(uri);
    toast.success('Redirect URI copiado');
  };

  if (!cfg) return <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Carregando...</p>;

  return (
    <div className="space-y-4">
      <div className="p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className="w-8 h-8 flex items-center justify-center text-sm font-bold" style={{ background: 'rgba(234,67,53,0.15)', color: '#EA4335' }}>G</span>
            <div>
              <h3 className="text-sm font-bold" style={{ fontFamily: 'Outfit, sans-serif' }}>Google OAuth App</h3>
              <p className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>Gmail · Drive · Sheets · Calendar · YouTube</p>
            </div>
          </div>
          {cfg.configured ? (
            <span className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider" style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--success)' }}>Configurado</span>
          ) : (
            <span className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--error)' }}>Pendente</span>
          )}
        </div>

        <div className="mb-4 p-3" style={{ background: 'var(--bg-base)' }}>
          <p className="text-[11px] font-bold uppercase tracking-wider mb-1" style={{ color: 'var(--text-tertiary)' }}>Redirect URI para colar no Google Cloud Console</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-[11px] truncate" style={{ color: 'var(--accent)' }}>{window.location.origin}/api/oauth/google/callback</code>
            <button data-testid="copy-redirect-uri" onClick={copyRedirect} className="p-1.5" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}><Copy className="w-3.5 h-3.5" /></button>
          </div>
        </div>

        <Input label="Client ID" value={form.client_id} onChange={v => setForm({ ...form, client_id: v })} testid="google-client-id" />
        <Input label={cfg.client_secret_set ? 'Client Secret (deixe em branco para não alterar)' : 'Client Secret'} type="password" value={form.client_secret} onChange={v => setForm({ ...form, client_secret: v })} testid="google-client-secret" />
        <label className="flex items-center gap-2 text-xs cursor-pointer mb-4">
          <input type="checkbox" checked={form.enabled} onChange={e => setForm({ ...form, enabled: e.target.checked })} data-testid="google-enabled-toggle" />
          <span style={{ color: 'var(--text-secondary)' }}>Habilitar integração Google para usuários</span>
        </label>

        <div className="flex gap-2">
          <button
            data-testid="save-google-config-btn"
            onClick={save}
            disabled={saving || !form.client_id || (!cfg.client_secret_set && !form.client_secret)}
            className="flex-1 py-2 text-xs font-bold disabled:opacity-50"
            style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}
          >{saving ? 'Salvando...' : 'Salvar'}</button>
          {cfg.configured && (
            <button data-testid="delete-google-config-btn" onClick={remove} className="px-4 py-2 text-xs font-bold" style={{ background: 'var(--bg-elevated)', color: 'var(--error)', border: '1px solid rgba(239,68,68,0.3)' }}>
              Remover
            </button>
          )}
        </div>

        <details className="mt-4">
          <summary className="text-[11px] cursor-pointer" style={{ color: 'var(--text-tertiary)' }}>Ver escopos autorizados ({cfg.scopes?.length || 0})</summary>
          <ul className="mt-2 text-[11px] space-y-0.5" style={{ color: 'var(--text-tertiary)' }}>
            {cfg.scopes?.map(s => <li key={s}>• {s.replace('https://www.googleapis.com/auth/', '')}</li>)}
          </ul>
        </details>
      </div>
    </div>
  );
}

// ─── Meta Card ────────────────────────────────────────────────────────────────
function MetaIntegrationCard({ api }) {
  const [cfg, setCfg] = useState(null);
  const [form, setForm] = useState({ app_id: '', app_secret: '', enabled: true });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/admin/integrations/meta');
      setCfg(data);
      setForm(f => ({ ...f, app_id: data.app_id || '', enabled: data.enabled }));
    } catch {}
  }, [api]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      await api.put('/admin/integrations/meta', form);
      toast.success('Meta App salvo');
      setForm(f => ({ ...f, app_secret: '' }));
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro'); }
    setSaving(false);
  };

  const remove = async () => {
    if (!window.confirm('Remover configuração Meta?')) return;
    await api.delete('/admin/integrations/meta');
    toast.success('Removido'); load();
  };

  const copyRedirect = () => {
    const uri = `${window.location.origin}/api/oauth/meta/callback`;
    navigator.clipboard.writeText(uri);
    toast.success('Redirect URI copiado');
  };

  if (!cfg) return null;

  return (
    <div className="p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="w-8 h-8 flex items-center justify-center text-sm font-bold" style={{ background: 'rgba(24,119,242,0.15)', color: '#1877f2' }}>f</span>
          <div>
            <h3 className="text-sm font-bold" style={{ fontFamily: 'Outfit, sans-serif' }}>Meta Business App</h3>
            <p className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>Instagram · Facebook Pages · WhatsApp · DMs</p>
          </div>
        </div>
        {cfg.configured ? (
          <span className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider" style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--success)' }}>Configurado</span>
        ) : (
          <span className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--error)' }}>Pendente</span>
        )}
      </div>

      <div className="mb-4 p-3" style={{ background: 'var(--bg-base)' }}>
        <p className="text-[11px] font-bold uppercase tracking-wider mb-1" style={{ color: 'var(--text-tertiary)' }}>Redirect URI para developers.facebook.com</p>
        <div className="flex items-center gap-2">
          <code className="flex-1 text-[11px] truncate" style={{ color: 'var(--accent)' }}>{window.location.origin}/api/oauth/meta/callback</code>
          <button data-testid="copy-meta-redirect" onClick={copyRedirect} className="p-1.5" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}><Copy className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      <Input label="App ID" value={form.app_id} onChange={v => setForm({ ...form, app_id: v })} testid="meta-app-id" />
      <Input label={cfg.app_secret_set ? 'App Secret (deixe em branco para não alterar)' : 'App Secret'} type="password" value={form.app_secret} onChange={v => setForm({ ...form, app_secret: v })} testid="meta-app-secret" />
      <label className="flex items-center gap-2 text-xs cursor-pointer mb-4">
        <input type="checkbox" checked={form.enabled} onChange={e => setForm({ ...form, enabled: e.target.checked })} data-testid="meta-enabled-toggle" />
        <span style={{ color: 'var(--text-secondary)' }}>Habilitar integração Meta</span>
      </label>

      <div className="flex gap-2">
        <button data-testid="save-meta-config-btn" onClick={save}
          disabled={saving || !form.app_id || (!cfg.app_secret_set && !form.app_secret)}
          className="flex-1 py-2 text-xs font-bold disabled:opacity-50"
          style={{ background: '#1877f2', color: '#ffffff' }}>{saving ? 'Salvando...' : 'Salvar'}</button>
        {cfg.configured && (
          <button data-testid="delete-meta-config-btn" onClick={remove} className="px-4 py-2 text-xs font-bold" style={{ background: 'var(--bg-elevated)', color: 'var(--error)', border: '1px solid rgba(239,68,68,0.3)' }}>Remover</button>
        )}
      </div>

      <details className="mt-4">
        <summary className="text-[11px] cursor-pointer" style={{ color: 'var(--text-tertiary)' }}>Ver escopos ({cfg.scopes?.length || 0})</summary>
        <ul className="mt-2 text-[11px] space-y-0.5" style={{ color: 'var(--text-tertiary)' }}>
          {cfg.scopes?.map(s => <li key={s}>• {s}</li>)}
        </ul>
      </details>
    </div>
  );
}

// ─── TikTok Card ──────────────────────────────────────────────────────────────
function TiktokIntegrationCard({ api }) {
  const [cfg, setCfg] = useState(null);
  const [form, setForm] = useState({ client_key: '', client_secret: '', enabled: true });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/admin/integrations/tiktok');
      setCfg(data);
      setForm(f => ({ ...f, client_key: data.client_key || '', enabled: data.enabled }));
    } catch {}
  }, [api]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      await api.put('/admin/integrations/tiktok', form);
      toast.success('TikTok App salvo');
      setForm(f => ({ ...f, client_secret: '' }));
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Erro'); }
    setSaving(false);
  };

  const remove = async () => {
    if (!window.confirm('Remover configuração TikTok?')) return;
    await api.delete('/admin/integrations/tiktok');
    toast.success('Removido'); load();
  };

  const copyRedirect = () => {
    const uri = `${window.location.origin}/api/oauth/tiktok/callback`;
    navigator.clipboard.writeText(uri);
    toast.success('Redirect URI copiado');
  };

  if (!cfg) return null;

  return (
    <div className="p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="w-8 h-8 flex items-center justify-center text-sm font-bold" style={{ background: 'rgba(255,0,80,0.15)', color: '#ff0050' }}>T</span>
          <div>
            <h3 className="text-sm font-bold" style={{ fontFamily: 'Outfit, sans-serif' }}>TikTok for Developers</h3>
            <p className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>Content Posting API · video.upload · video.publish</p>
          </div>
        </div>
        {cfg.configured ? (
          <span className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider" style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--success)' }}>Configurado</span>
        ) : (
          <span className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--error)' }}>Pendente</span>
        )}
      </div>

      <div className="mb-4 p-3" style={{ background: 'var(--bg-base)' }}>
        <p className="text-[11px] font-bold uppercase tracking-wider mb-1" style={{ color: 'var(--text-tertiary)' }}>Redirect URI para developers.tiktok.com</p>
        <div className="flex items-center gap-2">
          <code className="flex-1 text-[11px] truncate" style={{ color: 'var(--accent)' }}>{window.location.origin}/api/oauth/tiktok/callback</code>
          <button data-testid="copy-tiktok-redirect" onClick={copyRedirect} className="p-1.5" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}><Copy className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      <Input label="Client Key" value={form.client_key} onChange={v => setForm({ ...form, client_key: v })} testid="tiktok-client-key" />
      <Input label={cfg.client_secret_set ? 'Client Secret (deixe em branco para não alterar)' : 'Client Secret'} type="password" value={form.client_secret} onChange={v => setForm({ ...form, client_secret: v })} testid="tiktok-client-secret" />
      <label className="flex items-center gap-2 text-xs cursor-pointer mb-4">
        <input type="checkbox" checked={form.enabled} onChange={e => setForm({ ...form, enabled: e.target.checked })} data-testid="tiktok-enabled-toggle" />
        <span style={{ color: 'var(--text-secondary)' }}>Habilitar integração TikTok</span>
      </label>

      <div className="flex gap-2">
        <button data-testid="save-tiktok-config-btn" onClick={save}
          disabled={saving || !form.client_key || (!cfg.client_secret_set && !form.client_secret)}
          className="flex-1 py-2 text-xs font-bold disabled:opacity-50"
          style={{ background: '#ff0050', color: '#ffffff' }}>{saving ? 'Salvando...' : 'Salvar'}</button>
        {cfg.configured && (
          <button data-testid="delete-tiktok-config-btn" onClick={remove} className="px-4 py-2 text-xs font-bold" style={{ background: 'var(--bg-elevated)', color: 'var(--error)', border: '1px solid rgba(239,68,68,0.3)' }}>Remover</button>
        )}
      </div>

      <details className="mt-4">
        <summary className="text-[11px] cursor-pointer" style={{ color: 'var(--text-tertiary)' }}>Ver escopos ({cfg.scopes?.length || 0})</summary>
        <ul className="mt-2 text-[11px] space-y-0.5" style={{ color: 'var(--text-tertiary)' }}>
          {cfg.scopes?.map(s => <li key={s}>• {s}</li>)}
        </ul>
      </details>

      <p className="mt-3 text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
        Crie um app em <code>developers.tiktok.com</code>, adicione o produto <strong>Login Kit</strong> + <strong>Content Posting API</strong>, configure o Redirect URI acima e cole aqui o Client Key + Client Secret.
      </p>
    </div>
  );
}

