import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { X, ArrowLeft, RefreshCw, Cpu, HardDrive, BarChart3, Database, Users, MessageSquare, Zap, Brain } from 'lucide-react';

function Gauge({ value, label, color, max = 100 }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="p-3 text-center" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
      <div className="relative w-16 h-16 mx-auto mb-2">
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          <path d="M18 2.0845a 15.9155 15.9155 0 0 1 0 31.831a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="3" />
          <path d="M18 2.0845a 15.9155 15.9155 0 0 1 0 31.831a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={`${pct}, 100`} strokeLinecap="round" />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-sm font-bold font-mono">{Math.round(pct)}%</span>
      </div>
      <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
      <p className="text-xs font-mono" style={{ color }}>{value.toLocaleString()}{max !== 100 ? ` / ${max.toLocaleString()}` : ''}</p>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="p-3 flex items-center gap-3" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
      <div className="w-8 h-8 flex items-center justify-center flex-shrink-0" style={{ background: `${color}20`, border: `1px solid ${color}40` }}>
        <Icon className="w-4 h-4" style={{ color }} />
      </div>
      <div>
        <p className="text-lg font-bold font-mono">{typeof value === 'number' ? value.toLocaleString() : value}</p>
        <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
      </div>
    </div>
  );
}

export default function MonitorPanel({ onClose }) {
  const { api } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/system/memory-stats');
      setStats(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { load(); const i = setInterval(load, 10000); return () => clearInterval(i); }, []);

  const sys = stats?.system || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div data-testid="monitor-panel" className="w-full max-w-3xl animate-fade-in max-h-[90vh] flex flex-col"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="p-1.5" style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <h2 className="text-lg font-bold" style={{ fontFamily: 'Outfit' }}>Monitoramento do Sistema</h2>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Performance, recursos e estatisticas em tempo real</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={load} className="p-1.5" style={{ color: 'var(--text-tertiary)' }}><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /></button>
            <button onClick={onClose} style={{ color: 'var(--text-tertiary)' }}><X className="w-5 h-5" /></button>
          </div>
        </div>

        {stats && (
          <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
            {/* System resources */}
            <div>
              <p className="text-xs font-medium uppercase tracking-wider mb-3" style={{ color: 'var(--accent)' }}>Recursos do Sistema</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Gauge value={sys.ram_used_mb || 0} label="RAM Usada" color={sys.ram_percent > 80 ? '#EF4444' : sys.ram_percent > 60 ? '#F97316' : '#22C55E'} max={sys.ram_total_mb || 100} />
                <Gauge value={sys.ram_percent || 0} label="RAM %" color={sys.ram_percent > 80 ? '#EF4444' : '#22C55E'} />
                <Gauge value={sys.disk_percent || 0} label="Disco %" color={sys.disk_percent > 85 ? '#EF4444' : '#22C55E'} />
                <div className="p-3 text-center" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                  <Cpu className="w-6 h-6 mx-auto mb-2" style={{ color: 'var(--accent)' }} />
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Sistema</p>
                  <p className="text-xs font-mono">{sys.os} / Py {sys.python}</p>
                  <p className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>Disco: {sys.disk_free_gb}GB livre</p>
                </div>
              </div>
            </div>

            {/* AI Performance */}
            <div>
              <p className="text-xs font-medium uppercase tracking-wider mb-3" style={{ color: 'var(--accent)' }}>Performance da IA</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <StatCard icon={Brain} label="Cache de Respostas" value={stats.cache_entries} color="#FFD600" />
                <StatCard icon={Database} label="Resumos de Conversa" value={stats.conversation_summaries} color="#00C8FF" />
                <StatCard icon={Zap} label="Tarefas Pendentes" value={stats.tasks_pending} color="#F97316" />
                <StatCard icon={Zap} label="Tarefas Concluidas" value={stats.tasks_completed} color="#22C55E" />
              </div>
            </div>

            {/* Platform stats */}
            <div>
              <p className="text-xs font-medium uppercase tracking-wider mb-3" style={{ color: 'var(--accent)' }}>Estatisticas da Plataforma</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <StatCard icon={Users} label="Usuarios" value={stats.total_users} color="#A855F7" />
                <StatCard icon={MessageSquare} label="Mensagens" value={stats.total_messages} color="#3B82F6" />
                <StatCard icon={MessageSquare} label="Conversas" value={stats.total_conversations} color="#00C8FF" />
                <StatCard icon={BarChart3} label="Agentes Criados" value={stats.total_agents} color="#FFD600" />
              </div>
              <div className="grid grid-cols-3 gap-3 mt-3">
                <StatCard icon={HardDrive} label="Produtos" value={stats.total_products} color="#22C55E" />
                <StatCard icon={Zap} label="Regras Ativas" value={stats.active_rules} color="#F97316" />
                <StatCard icon={Database} label="Mentorias" value={stats.total_mentorships} color="#A855F7" />
              </div>
            </div>

            {/* Info */}
            <div className="p-3" style={{ background: 'var(--terminal-bg)', border: '1px solid var(--border-subtle)' }}>
              <p className="text-xs font-mono" style={{ color: 'var(--terminal-text)' }}>
                Atualiza automaticamente a cada 10 segundos. RAM e disco sao do servidor onde o sistema esta rodando.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
