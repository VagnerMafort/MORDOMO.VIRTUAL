import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { X, Mic, MicOff, Volume2, VolumeX, Loader2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATES = { IDLE: 'idle', LISTENING: 'listening', PROCESSING: 'processing', SPEAKING: 'speaking' };

export default function HandsFreeMode({ onClose, agentName }) {
  const { api, getToken } = useAuth();
  const [state, setState] = useState(STATES.IDLE);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [convId, setConvId] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState('');
  const recognitionRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);
  const autoRestart = useRef(true);

  // Create conversation on mount
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.post('/conversations', { title: `[Voz] ${agentName || 'NovaClaw'}` });
        setConvId(data.id);
      } catch (e) { console.error(e); }
    })();
    return () => {
      autoRestart.current = false;
      recognitionRef.current?.stop();
      synthRef.current?.cancel();
    };
  }, [api, agentName]);

  // Setup speech recognition
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setError('Seu navegador nao suporta reconhecimento de voz'); return; }
    const rec = new SR();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = 'pt-BR';
    rec.maxAlternatives = 1;

    rec.onresult = (e) => {
      let final = '';
      let interim = '';
      for (let i = 0; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          final += e.results[i][0].transcript;
        } else {
          interim += e.results[i][0].transcript;
        }
      }
      setTranscript(final || interim);
    };

    rec.onend = () => {
      // If we got a final transcript, send it
      setTranscript(prev => {
        if (prev.trim() && autoRestart.current) {
          sendMessage(prev.trim());
        } else if (autoRestart.current && state === STATES.LISTENING) {
          // Restart listening if no speech detected
          try { rec.start(); } catch {}
        }
        return prev;
      });
    };

    rec.onerror = (e) => {
      if (e.error === 'no-speech' && autoRestart.current) {
        try { rec.start(); } catch {}
      } else if (e.error !== 'aborted') {
        console.error('Speech error:', e.error);
      }
    };

    recognitionRef.current = rec;
  }, []);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    synthRef.current?.cancel();
    setTranscript('');
    setResponse('');
    setState(STATES.LISTENING);
    try { recognitionRef.current.start(); } catch {}
  }, []);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    autoRestart.current = false;
    setState(STATES.IDLE);
  }, []);

  const sendMessage = useCallback(async (text) => {
    if (!text || !convId) return;
    setState(STATES.PROCESSING);
    setHistory(prev => [...prev, { role: 'user', text }]);
    setTranscript('');

    try {
      const res = await fetch(`${BACKEND_URL}/api/conversations/${convId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
        body: JSON.stringify({ content: text }),
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'token') {
              fullContent += data.content;
              setResponse(fullContent);
            } else if (data.type === 'done') {
              setHistory(prev => [...prev, { role: 'assistant', text: fullContent }]);
              speakResponse(fullContent);
            }
          } catch {}
        }
      }
    } catch (e) {
      console.error(e);
      setState(STATES.IDLE);
      if (autoRestart.current) startListening();
    }
  }, [convId, getToken, startListening]);

  const speakResponse = useCallback((text) => {
    setState(STATES.SPEAKING);
    const clean = text
      .replace(/```[\s\S]*?```/g, '')
      .replace(/`[^`]+`/g, '')
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/\*(.+?)\*/g, '$1')
      .replace(/#{1,3}\s/g, '')
      .replace(/\[SKILL:[^\]]+\][^`]*/g, '')
      .replace(/https?:\/\/\S+/g, '')
      .trim();

    if (!clean || !synthRef.current) {
      setState(STATES.IDLE);
      if (autoRestart.current) setTimeout(startListening, 500);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(clean.slice(0, 800));
    utterance.lang = 'pt-BR';
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    utterance.onend = () => {
      setState(STATES.IDLE);
      if (autoRestart.current) setTimeout(startListening, 300);
    };
    utterance.onerror = () => {
      setState(STATES.IDLE);
      if (autoRestart.current) setTimeout(startListening, 300);
    };
    synthRef.current.speak(utterance);
  }, [startListening]);

  const toggleMode = () => {
    if (state === STATES.IDLE) {
      autoRestart.current = true;
      startListening();
    } else {
      autoRestart.current = false;
      recognitionRef.current?.stop();
      synthRef.current?.cancel();
      setState(STATES.IDLE);
    }
  };

  const handleClose = () => {
    autoRestart.current = false;
    recognitionRef.current?.stop();
    synthRef.current?.cancel();
    onClose();
  };

  const stateConfig = {
    [STATES.IDLE]: { label: 'Toque para comecar', color: 'var(--text-tertiary)', pulse: false },
    [STATES.LISTENING]: { label: 'Ouvindo...', color: 'var(--accent)', pulse: true },
    [STATES.PROCESSING]: { label: 'Pensando...', color: 'var(--info)', pulse: false },
    [STATES.SPEAKING]: { label: 'Respondendo...', color: 'var(--success)', pulse: true },
  };

  const cfg = stateConfig[state];

  return (
    <div className="fixed inset-0 z-50 flex flex-col" style={{ background: 'var(--bg-base)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4">
        <div>
          <h2 className="text-lg font-bold" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Modo Maos Livres
          </h2>
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            Conversa por voz com {agentName || 'NovaClaw'}
          </p>
        </div>
        <button data-testid="close-handsfree-btn" onClick={handleClose}
          className="p-2" style={{ color: 'var(--text-tertiary)' }}>
          <X className="w-6 h-6" />
        </button>
      </div>

      {/* Main area */}
      <div className="flex-1 flex flex-col items-center justify-center px-6">
        {error && (
          <p className="text-sm mb-8 text-center" style={{ color: 'var(--error)' }}>{error}</p>
        )}

        {/* Conversation history (last 2 exchanges) */}
        <div className="w-full max-w-md mb-8 flex flex-col gap-3">
          {history.slice(-4).map((h, i) => (
            <div key={i} className="animate-fade-in">
              <p className="text-xs font-medium mb-1" style={{ color: h.role === 'user' ? 'var(--text-tertiary)' : 'var(--accent)', fontFamily: 'Outfit' }}>
                {h.role === 'user' ? 'Voce' : agentName || 'NovaClaw'}
              </p>
              <p className="text-sm leading-relaxed" style={{ color: h.role === 'user' ? 'var(--text-secondary)' : 'var(--text-primary)' }}>
                {h.text.length > 200 ? h.text.slice(0, 200) + '...' : h.text}
              </p>
            </div>
          ))}
        </div>

        {/* Central mic button */}
        <button
          data-testid="handsfree-mic-btn"
          onClick={toggleMode}
          className="relative w-28 h-28 rounded-full flex items-center justify-center transition-all"
          style={{
            background: state === STATES.IDLE ? 'var(--bg-surface)' : 'transparent',
            border: `3px solid ${cfg.color}`,
          }}
        >
          {/* Pulse ring */}
          {cfg.pulse && (
            <>
              <span className="absolute inset-0 rounded-full animate-ping opacity-20" style={{ background: cfg.color }} />
              <span className="absolute inset-[-8px] rounded-full opacity-10" style={{ background: cfg.color, animation: 'pulse-ring 2s infinite' }} />
            </>
          )}

          {state === STATES.PROCESSING ? (
            <Loader2 className="w-10 h-10 animate-spin" style={{ color: cfg.color }} />
          ) : state === STATES.SPEAKING ? (
            <Volume2 className="w-10 h-10" style={{ color: cfg.color }} />
          ) : state === STATES.LISTENING ? (
            <Mic className="w-10 h-10" style={{ color: cfg.color }} />
          ) : (
            <MicOff className="w-10 h-10" style={{ color: cfg.color }} />
          )}
        </button>

        {/* State label */}
        <p className="mt-6 text-sm font-medium" style={{ color: cfg.color, fontFamily: 'Outfit' }}>
          {cfg.label}
        </p>

        {/* Live transcript */}
        {transcript && state === STATES.LISTENING && (
          <p className="mt-4 text-lg text-center animate-fade-in max-w-md" style={{ color: 'var(--text-primary)' }}>
            "{transcript}"
          </p>
        )}

        {/* Live response */}
        {response && (state === STATES.PROCESSING || state === STATES.SPEAKING) && (
          <p className="mt-4 text-sm text-center max-w-md leading-relaxed animate-fade-in" style={{ color: 'var(--text-secondary)' }}>
            {response.length > 300 ? response.slice(0, 300) + '...' : response}
          </p>
        )}
      </div>

      {/* Footer hint */}
      <div className="px-6 py-4 text-center">
        <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
          {state === STATES.IDLE
            ? 'Toque no microfone para iniciar a conversa por voz'
            : state === STATES.LISTENING
              ? 'Fale agora - envio automatico quando parar de falar'
              : state === STATES.SPEAKING
                ? 'Ouca a resposta - volta a ouvir automaticamente'
                : 'Processando sua mensagem...'
          }
        </p>
      </div>
    </div>
  );
}
