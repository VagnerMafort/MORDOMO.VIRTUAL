import { useAuth } from '@/contexts/AuthContext';
import { Plus, Settings, Cpu, Trash2, MessageSquare, LogOut, Zap, Pencil, Check, X, Bot, Building2, GraduationCap, Activity, Shield, Plug, Workflow, Share2 } from 'lucide-react';
import { useState } from 'react';

export default function Sidebar({ conversations, activeConvId, onSelect, onCreate, onDelete, onRename, onOpenSettings, onOpenSkills, onOpenAgents, onOpenAgency, onOpenMentorship, onOpenMonitor, onOpenAdmin, onOpenIntegrations, onOpenWorkflows, onOpenSocial, agentName, allowedModules = [] }) {
  const { user, logout } = useAuth();
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const canSee = (key) => allowedModules.length === 0 || allowedModules.includes(key) || user?.role === 'admin';

  const startEdit = (conv) => {
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const saveEdit = () => {
    if (editTitle.trim()) onRename(editingId, editTitle.trim());
    setEditingId(null);
  };

  return (
    <div
      data-testid="sidebar"
      className="h-full flex flex-col"
      style={{ background: 'var(--bg-surface)', borderRight: '1px solid var(--border-subtle)' }}
    >
      {/* Header */}
      <div className="p-4 flex items-center gap-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <div className="w-8 h-8 flex items-center justify-center flex-shrink-0" style={{ background: 'var(--accent)' }}>
          <Zap className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
        </div>
        <div className="min-w-0">
          <h2 className="text-sm font-bold tracking-tight truncate" style={{ fontFamily: 'Outfit, sans-serif' }}>{agentName || 'Mordomo Virtual'}</h2>
          <p className="text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>{user?.name || user?.email}</p>
        </div>
      </div>

      {/* New chat button */}
      <div className="p-3">
        <button
          data-testid="new-chat-btn"
          onClick={onCreate}
          className="w-full py-2.5 px-4 text-sm font-medium flex items-center gap-2 transition-colors"
          style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--accent-hover)'}
          onMouseLeave={e => e.currentTarget.style.background = 'var(--accent)'}
        >
          <Plus className="w-4 h-4" />
          Nova Conversa
        </button>
      </div>

      {/* Conversations list */}
      <div className="flex-1 overflow-y-auto px-2">
        <p className="px-2 py-2 text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
          Historico
        </p>
        {conversations.length === 0 && (
          <p className="px-3 py-4 text-xs text-center" style={{ color: 'var(--text-tertiary)' }}>
            Nenhuma conversa ainda
          </p>
        )}
        {conversations.map(conv => (
          <div
            key={conv.id}
            data-testid={`conversation-item-${conv.id}`}
            className="group flex items-center gap-1 px-3 py-2.5 mb-0.5 cursor-pointer transition-colors"
            style={{
              background: conv.id === activeConvId ? 'var(--bg-elevated)' : 'transparent',
              borderLeft: conv.id === activeConvId ? '2px solid var(--accent)' : '2px solid transparent',
            }}
            onClick={() => editingId !== conv.id && onSelect(conv.id)}
            onMouseEnter={e => { if (conv.id !== activeConvId) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
            onMouseLeave={e => { if (conv.id !== activeConvId) e.currentTarget.style.background = 'transparent'; }}
          >
            <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--text-tertiary)' }} />
            {editingId === conv.id ? (
              <div className="flex-1 flex items-center gap-1 min-w-0">
                <input
                  value={editTitle}
                  onChange={e => setEditTitle(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && saveEdit()}
                  className="flex-1 text-xs py-0.5 px-1 outline-none min-w-0"
                  style={{ background: 'var(--bg-base)', border: '1px solid var(--accent)', color: 'var(--text-primary)' }}
                  autoFocus
                />
                <button onClick={saveEdit} style={{ color: 'var(--success)' }}><Check className="w-3.5 h-3.5" /></button>
                <button onClick={() => setEditingId(null)} style={{ color: 'var(--error)' }}><X className="w-3.5 h-3.5" /></button>
              </div>
            ) : (
              <>
                <span className="flex-1 text-xs truncate" style={{ color: conv.id === activeConvId ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                  {conv.title}
                </span>
                <div className="hidden group-hover:flex items-center gap-0.5">
                  <button
                    data-testid={`rename-conv-${conv.id}`}
                    onClick={(e) => { e.stopPropagation(); startEdit(conv); }}
                    className="p-1 transition-colors"
                    style={{ color: 'var(--text-tertiary)' }}
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                  <button
                    data-testid={`delete-conv-${conv.id}`}
                    onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}
                    className="p-1 transition-colors"
                    style={{ color: 'var(--text-tertiary)' }}
                    onMouseEnter={e => e.currentTarget.style.color = 'var(--error)'}
                    onMouseLeave={e => e.currentTarget.style.color = 'var(--text-tertiary)'}
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      {/* Bottom actions */}
      <div className="p-3 flex flex-col gap-1" style={{ borderTop: '1px solid var(--border-subtle)' }}>
        {canSee('agents') && (
          <button
            data-testid="open-agents-btn"
            onClick={onOpenAgents}
            className="w-full py-2 px-3 text-xs font-medium flex items-center gap-2 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
          >
            <Bot className="w-4 h-4" /> Meus Agentes
          </button>
        )}
        {onOpenAgency && canSee('agency') && (
          <button
            data-testid="open-agency-btn"
            onClick={onOpenAgency}
            className="w-full py-2 px-3 text-xs font-medium flex items-center gap-2 transition-colors"
            style={{ color: 'var(--accent)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,214,0,0.08)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >
            <Building2 className="w-4 h-4" /> Agencia
          </button>
        )}
        {canSee('mentorship') && (
          <button
            data-testid="open-mentorship-btn"
            onClick={onOpenMentorship}
            className="w-full py-2 px-3 text-xs font-medium flex items-center gap-2 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
          >
            <GraduationCap className="w-4 h-4" /> Criar Mentoria
          </button>
        )}
        {canSee('skills') && (
          <button
            data-testid="open-skills-btn"
            onClick={onOpenSkills}
            className="w-full py-2 px-3 text-xs font-medium flex items-center gap-2 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
          >
            <Cpu className="w-4 h-4" /> Habilidades do Agente
          </button>
        )}
        {canSee('monitor') && (
          <button
            data-testid="open-monitor-btn"
            onClick={onOpenMonitor}
            className="w-full py-2 px-3 text-xs font-medium flex items-center gap-2 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
          >
            <Activity className="w-4 h-4" /> Monitoramento
          </button>
        )}
        <button
          data-testid="open-integrations-btn"
          onClick={onOpenIntegrations}
          className="w-full py-2 px-3 text-xs font-medium flex items-center gap-2 transition-colors"
          style={{ color: 'var(--text-secondary)' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
        >
          <Plug className="w-4 h-4" /> Minhas Integrações
        </button>
        {canSee('workflows') && (
          <button
            data-testid="open-workflows-btn"
            onClick={onOpenWorkflows}
            className="w-full py-2 px-3 text-xs font-medium flex items-center gap-2 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
          >
            <Workflow className="w-4 h-4" /> Fluxos de Trabalho
          </button>
        )}
        {canSee('social') && onOpenSocial && (
          <button
            data-testid="open-social-btn"
            onClick={onOpenSocial}
            className="w-full py-2 px-3 text-xs font-medium flex items-center gap-2 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
          >
            <Share2 className="w-4 h-4" /> Publicar em Redes
          </button>
        )}
        {user?.role === 'admin' && onOpenAdmin && (
          <button
            data-testid="open-admin-btn"
            onClick={onOpenAdmin}
            className="w-full py-2 px-3 text-xs font-bold flex items-center gap-2 transition-colors"
            style={{ color: 'var(--accent)', background: 'rgba(255,214,0,0.05)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,214,0,0.12)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,214,0,0.05)'; }}
          >
            <Shield className="w-4 h-4" /> Painel Admin
          </button>
        )}
        <button
          data-testid="open-settings-btn"
          onClick={onOpenSettings}
          className="w-full py-2 px-3 text-xs font-medium flex items-center gap-2 transition-colors"
          style={{ color: 'var(--text-secondary)' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
        >
          <Settings className="w-4 h-4" /> Configuracoes
        </button>
        <button
          data-testid="logout-btn"
          onClick={logout}
          className="w-full py-2 px-3 text-xs font-medium flex items-center gap-2 transition-colors"
          style={{ color: 'var(--text-tertiary)' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.1)'; e.currentTarget.style.color = 'var(--error)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-tertiary)'; }}
        >
          <LogOut className="w-4 h-4" /> Desconectar
        </button>
      </div>
    </div>
  );
}
