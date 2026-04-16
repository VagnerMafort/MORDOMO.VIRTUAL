import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import Sidebar from '@/components/Sidebar';
import ChatArea from '@/components/ChatArea';
import SettingsPanel from '@/components/SettingsPanel';
import SkillsDashboard from '@/components/SkillsDashboard';
import AgentManager from '@/components/AgentManager';
import { Menu } from 'lucide-react';

export default function ChatPage() {
  const { api } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showSkills, setShowSkills] = useState(false);
  const [showAgents, setShowAgents] = useState(false);

  const fetchConversations = useCallback(async () => {
    try {
      const { data } = await api.get('/conversations');
      setConversations(data);
    } catch (e) {
      console.error('Erro ao carregar conversas:', e);
    }
  }, [api]);

  useEffect(() => { fetchConversations(); }, [fetchConversations]);

  const createConversation = async () => {
    try {
      const { data } = await api.post('/conversations', { title: 'Nova Conversa' });
      setConversations(prev => [data, ...prev]);
      setActiveConvId(data.id);
      setSidebarOpen(false);
    } catch (e) {
      console.error('Erro ao criar conversa:', e);
    }
  };

  const deleteConversation = async (convId) => {
    try {
      await api.delete(`/conversations/${convId}`);
      setConversations(prev => prev.filter(c => c.id !== convId));
      if (activeConvId === convId) setActiveConvId(null);
    } catch (e) {
      console.error('Erro ao deletar conversa:', e);
    }
  };

  const renameConversation = async (convId, newTitle) => {
    try {
      await api.put(`/conversations/${convId}`, { title: newTitle });
      setConversations(prev => prev.map(c => c.id === convId ? { ...c, title: newTitle } : c));
    } catch (e) {
      console.error('Erro ao renomear conversa:', e);
    }
  };

  const onConversationUpdated = (convId, title) => {
    setConversations(prev => prev.map(c => c.id === convId ? { ...c, title, updated_at: new Date().toISOString() } : c));
  };

  const startAgentChat = async (agent) => {
    try {
      const { data } = await api.post('/conversations', { title: `[${agent.name}] Nova Conversa`, agent_id: agent.id });
      setConversations(prev => [data, ...prev]);
      setActiveConvId(data.id);
      setShowAgents(false);
      setSidebarOpen(false);
    } catch (e) { console.error(e); }
  };

  return (
    <div data-testid="chat-page" className="h-screen flex overflow-hidden" style={{ background: 'var(--bg-base)' }}>
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-40 w-72 transform transition-transform duration-200 lg:relative lg:translate-x-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <Sidebar
          conversations={conversations}
          activeConvId={activeConvId}
          onSelect={(id) => { setActiveConvId(id); setSidebarOpen(false); }}
          onCreate={createConversation}
          onDelete={deleteConversation}
          onRename={renameConversation}
          onOpenSettings={() => { setShowSettings(true); setSidebarOpen(false); }}
          onOpenSkills={() => { setShowSkills(true); setSidebarOpen(false); }}
          onOpenAgents={() => { setShowAgents(true); setSidebarOpen(false); }}
        />
      </div>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        <div className="flex items-center gap-3 px-4 py-3 lg:hidden" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <button
            data-testid="mobile-menu-btn"
            onClick={() => setSidebarOpen(true)}
            className="p-2 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
          >
            <Menu className="w-5 h-5" />
          </button>
          <h1 className="text-sm font-semibold truncate" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {conversations.find(c => c.id === activeConvId)?.title || 'NovaClaw'}
          </h1>
        </div>

        <ChatArea
          conversationId={activeConvId}
          onConversationUpdated={onConversationUpdated}
          onCreateConversation={async () => {
            const { data } = await api.post('/conversations', { title: 'Nova Conversa' });
            setConversations(prev => [data, ...prev]);
            setActiveConvId(data.id);
            return data.id;
          }}
        />
      </div>

      {/* Settings Modal */}
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
      {/* Skills Modal */}
      {showSkills && <SkillsDashboard onClose={() => setShowSkills(false)} />}
      {/* Agents Modal */}
      {showAgents && <AgentManager onClose={() => setShowAgents(false)} onStartChat={startAgentChat} />}
    </div>
  );
}
