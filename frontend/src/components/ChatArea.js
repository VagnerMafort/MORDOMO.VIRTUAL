import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import MessageInput from '@/components/MessageInput';
import { Bot, User, Zap, Volume2, VolumeX } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function speakText(text, lang = 'pt-BR') {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  // Strip markdown/code for clean speech
  const clean = text
    .replace(/```[\s\S]*?```/g, 'bloco de codigo')
    .replace(/`[^`]+`/g, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/#{1,3}\s/g, '')
    .replace(/\[SKILL:[^\]]+\]/g, '')
    .replace(/https?:\/\/\S+/g, 'link')
    .trim();
  if (!clean) return;
  const utterance = new SpeechSynthesisUtterance(clean.slice(0, 500));
  utterance.lang = lang;
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  window.speechSynthesis.speak(utterance);
}

function formatContent(text) {
  if (!text) return '';
  // Basic markdown-like rendering
  let html = text
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/\n/g, '<br/>');
  // Wrap consecutive <li> in <ul>
  html = html.replace(/(<li>.*?<\/li>(<br\/>)?)+/g, (match) => {
    return '<ul>' + match.replace(/<br\/>/g, '') + '</ul>';
  });
  return html;
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 px-4 py-3 animate-fade-in">
      <div className="w-7 h-7 flex-shrink-0 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
        <Bot className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
      </div>
      <div className="typing-indicator flex gap-1.5 pt-2">
        <span className="w-2 h-2 rounded-full" style={{ background: 'var(--accent)' }} />
        <span className="w-2 h-2 rounded-full" style={{ background: 'var(--accent)' }} />
        <span className="w-2 h-2 rounded-full" style={{ background: 'var(--accent)' }} />
      </div>
    </div>
  );
}

export default function ChatArea({ conversationId, onConversationUpdated, onCreateConversation }) {
  const { api, getToken } = useAuth();
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState('');
  const [ttsActive, setTtsActive] = useState(() => localStorage.getItem('nc_tts') !== 'false');
  const scrollRef = useRef(null);
  const abortRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    if (!conversationId) { setMessages([]); return; }
    (async () => {
      try {
        const { data } = await api.get(`/conversations/${conversationId}/messages`);
        setMessages(data);
        setTimeout(scrollToBottom, 50);
      } catch (e) {
        console.error(e);
      }
    })();
  }, [conversationId, api, scrollToBottom]);

  useEffect(() => { scrollToBottom(); }, [messages, streamContent, scrollToBottom]);

  const sendMessage = async (content) => {
    let convId = conversationId;
    if (!convId) {
      convId = await onCreateConversation();
    }

    // Add user message optimistically
    const userMsg = { id: Date.now().toString(), role: 'user', content, created_at: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setStreaming(true);
    setStreamContent('');

    try {
      const response = await fetch(`${BACKEND_URL}/api/conversations/${convId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ content }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'token') {
              fullContent += data.content;
              setStreamContent(fullContent);
            } else if (data.type === 'done') {
              setMessages(prev => [
                ...prev,
                { id: data.message_id, role: 'assistant', content: fullContent, created_at: new Date().toISOString() }
              ]);
              setStreamContent('');
              setStreaming(false);
              // TTS: read response aloud
              if (ttsActive && fullContent) {
                speakText(fullContent);
              }
              // Update conversation title
              if (messages.length === 0) {
                const title = content.slice(0, 50) + (content.length > 50 ? '...' : '');
                onConversationUpdated(convId, title);
              }
            }
          } catch {}
        }
      }
    } catch (e) {
      console.error('Stream error:', e);
      setStreaming(false);
      setStreamContent('');
    }
  };

  // Empty state
  if (!conversationId && messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex-1 flex items-center justify-center px-6 overflow-y-auto">
          <div className="text-center animate-fade-in max-w-lg">
            <img src="/kaelum-icon.png" alt="Kaelum.AI" className="w-16 h-16 mx-auto mb-6 object-contain" />
            <h2 className="text-2xl font-black tracking-tighter mb-3" style={{ fontFamily: 'Outfit, sans-serif', color: 'var(--text-primary)' }}>
              Kaelum<span style={{ color: 'var(--accent-soft)' }}>.AI</span>
            </h2>
            <p className="text-sm mb-6" style={{ color: 'var(--text-secondary)' }}>
              Assistente virtual inteligente. Pergunte qualquer coisa, execute tarefas, automatize processos.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                'Como posso automatizar tarefas?',
                'Extraia dados de uma pagina web',
                'Que horas sao agora?',
                'Execute um calculo complexo',
              ].map((q, i) => (
                <button
                  key={i}
                  data-testid={`suggestion-${i}`}
                  onClick={() => sendMessage(q)}
                  className="text-left text-xs p-3 transition-colors"
                  style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-subtle)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
        <MessageInput onSend={sendMessage} disabled={streaming} />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* TTS toggle bar */}
      <div className="hidden lg:flex items-center justify-between px-4 py-2" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <h3 className="text-sm font-medium truncate" style={{ fontFamily: 'Outfit, sans-serif', color: 'var(--text-secondary)' }}>
          {messages.length > 0 ? 'Conversa ativa' : 'Kaelum.AI'}
        </h3>
        <button
          data-testid="tts-chat-toggle"
          onClick={() => { setTtsActive(p => { localStorage.setItem('nc_tts', !p); return !p; }); }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors"
          style={{
            background: ttsActive ? 'rgba(255,214,0,0.1)' : 'transparent',
            border: `1px solid ${ttsActive ? 'rgba(255,214,0,0.3)' : 'var(--border-subtle)'}`,
            color: ttsActive ? 'var(--accent)' : 'var(--text-tertiary)',
          }}
        >
          {ttsActive ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
          {ttsActive ? 'TTS Ativo' : 'TTS Desligado'}
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto" data-testid="messages-container">
        <div className="max-w-3xl mx-auto py-4">
          {messages.map((msg, idx) => (
            <div
              key={msg.id || idx}
              className="flex items-start gap-3 px-4 py-3 animate-fade-in"
              style={{ animationDelay: `${idx * 30}ms` }}
            >
              {msg.role === 'user' ? (
                <div className="w-7 h-7 flex-shrink-0 flex items-center justify-center" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                  <User className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
                </div>
              ) : (
                <div className="w-7 h-7 flex-shrink-0 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
                  <Bot className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
                </div>
              )}
              <div className="min-w-0 flex-1 pt-0.5">
                <p className="text-xs font-medium mb-1" style={{ color: msg.role === 'user' ? 'var(--text-primary)' : 'var(--accent)', fontFamily: 'Outfit, sans-serif' }}>
                  {msg.role === 'user' ? 'Voce' : 'Kaelum.AI'}
                </p>
                {msg.role === 'user' ? (
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>{msg.content}</p>
                ) : (
                  <div
                    className="msg-content text-sm leading-relaxed"
                    style={{ color: 'var(--text-secondary)' }}
                    dangerouslySetInnerHTML={{ __html: formatContent(msg.content) }}
                  />
                )}
              </div>
            </div>
          ))}

          {/* Streaming message */}
          {streaming && streamContent && (
            <div className="flex items-start gap-3 px-4 py-3 animate-fade-in">
              <div className="w-7 h-7 flex-shrink-0 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
                <Bot className="w-4 h-4" style={{ color: 'var(--accent-text)' }} />
              </div>
              <div className="min-w-0 flex-1 pt-0.5">
                <p className="text-xs font-medium mb-1" style={{ color: 'var(--accent)', fontFamily: 'Outfit, sans-serif' }}>Kaelum.AI</p>
                <div
                  className="msg-content text-sm leading-relaxed"
                  style={{ color: 'var(--text-secondary)' }}
                  dangerouslySetInnerHTML={{ __html: formatContent(streamContent) }}
                />
              </div>
            </div>
          )}

          {streaming && !streamContent && <TypingIndicator />}
        </div>
      </div>

      <MessageInput onSend={sendMessage} disabled={streaming} />
    </div>
  );
}
