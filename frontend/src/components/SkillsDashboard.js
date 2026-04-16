import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { X, Globe, Calculator, Terminal, Cpu, Clock, FolderOpen, Monitor, Timer, Mail, Zap, ArrowLeft, Code, FileText, ClipboardList, Search, BarChart3 } from 'lucide-react';

const ICON_MAP = {
  Globe, Calculator, Terminal, Cpu, Clock, FolderOpen, Monitor, Timer, Mail, Zap,
  Code, FileText, ClipboardList, Search, BarChart3,
};

export default function SkillsDashboard({ onClose }) {
  const { api } = useAuth();
  const [skills, setSkills] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/skills');
        setSkills(data);
      } catch (e) {
        console.error(e);
      }
    })();
  }, [api]);

  const toggleSkill = async (skillId) => {
    try {
      const { data } = await api.post(`/skills/${skillId}/toggle`);
      setSkills(prev => prev.map(s => ({ ...s, enabled: data.enabled.includes(s.id) })));
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div
        data-testid="skills-dashboard"
        className="w-full max-w-2xl animate-fade-in max-h-[85vh] overflow-y-auto"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <button
              data-testid="skills-back-btn"
              onClick={onClose}
              className="p-1.5 transition-colors"
              style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-subtle)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <h2 className="text-lg font-bold tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>Habilidades do Agente</h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
                Ative ou desative as capacidades do Mordomo Virtual
              </p>
            </div>
          </div>
          <button data-testid="close-skills-btn" onClick={onClose} style={{ color: 'var(--text-tertiary)' }} className="p-1 transition-colors hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {skills.map(skill => {
            const IconComp = ICON_MAP[skill.icon] || Zap;
            return (
              <div
                key={skill.id}
                data-testid={`skill-card-${skill.id}`}
                className="flex items-start gap-3 p-4 transition-all cursor-pointer"
                style={{
                  background: skill.enabled ? 'rgba(255,214,0,0.05)' : 'var(--bg-elevated)',
                  border: `1px solid ${skill.enabled ? 'rgba(255,214,0,0.3)' : 'var(--border-subtle)'}`,
                }}
                onClick={() => toggleSkill(skill.id)}
              >
                <div
                  className="w-9 h-9 flex-shrink-0 flex items-center justify-center"
                  style={{
                    background: skill.enabled ? 'var(--accent)' : 'var(--bg-base)',
                    border: skill.enabled ? 'none' : '1px solid var(--border-subtle)',
                  }}
                >
                  <IconComp className="w-4 h-4" style={{ color: skill.enabled ? 'var(--accent-text)' : 'var(--text-tertiary)' }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium" style={{ color: skill.enabled ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                      {skill.name}
                    </p>
                    <div
                      className="w-8 h-5 flex-shrink-0 relative transition-colors"
                      style={{ background: skill.enabled ? 'var(--accent)' : 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}
                    >
                      <span
                        className="absolute top-0.5 w-3 h-3 transition-transform"
                        style={{
                          background: skill.enabled ? 'var(--accent-text)' : 'var(--text-tertiary)',
                          left: skill.enabled ? '16px' : '2px'
                        }}
                      />
                    </div>
                  </div>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
                    {skill.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="p-5" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          <div className="p-3" style={{ background: 'var(--terminal-bg)', border: '1px solid var(--border-subtle)' }}>
            <p className="text-xs font-mono" style={{ color: 'var(--terminal-text)' }}>
              Skills com acesso total ao sistema (Browser, Cron, E-mail) requerem deploy na VPS com permissoes configuradas.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
