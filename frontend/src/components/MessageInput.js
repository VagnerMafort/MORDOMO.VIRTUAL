import { useState, useRef, useEffect } from 'react';
import { Send, Mic, MicOff, Square } from 'lucide-react';

export default function MessageInput({ onSend, disabled }) {
  const [text, setText] = useState('');
  const [listening, setListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const recognitionRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR) {
      setVoiceSupported(true);
      const rec = new SR();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = 'pt-BR';
      rec.onresult = (e) => {
        let transcript = '';
        for (let i = 0; i < e.results.length; i++) {
          transcript += e.results[i][0].transcript;
        }
        setText(transcript);
      };
      rec.onend = () => setListening(false);
      rec.onerror = () => setListening(false);
      recognitionRef.current = rec;
    }
  }, []);

  const toggleVoice = () => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      // Auto-send after stopping voice
      if (text.trim()) {
        onSend(text.trim());
        setText('');
      }
    } else {
      setText('');
      recognitionRef.current?.start();
      setListening(true);
    }
  };

  const handleSend = () => {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e) => {
    setText(e.target.value);
    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
  };

  return (
    <div className="kaelum-input-safe px-3 pb-3 pt-2 sm:px-6 sm:pb-4" style={{ background: 'var(--bg-base)' }}>
      <div
        data-testid="message-input-container"
        className="max-w-3xl mx-auto flex items-end gap-2 p-2"
        style={{ background: 'var(--bg-surface)', border: `1px solid ${listening ? 'var(--accent)' : 'var(--border-subtle)'}` }}
      >
        {/* Voice button */}
        {voiceSupported && (
          <button
            data-testid="voice-mode-toggle"
            onClick={toggleVoice}
            className={`flex-shrink-0 p-2.5 transition-all ${listening ? 'voice-pulse' : ''}`}
            style={{
              background: listening ? 'var(--accent)' : 'transparent',
              color: listening ? 'var(--accent-text)' : 'var(--text-tertiary)',
            }}
            title={listening ? 'Parar de ouvir' : 'Modo Voz'}
          >
            {listening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>
        )}

        {/* Text input */}
        <textarea
          ref={textareaRef}
          data-testid="message-input"
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={listening ? 'Ouvindo...' : 'Digite sua mensagem aqui...'}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm outline-none py-2.5 px-2 min-h-[40px]"
          style={{ color: 'var(--text-primary)', maxHeight: '160px' }}
        />

        {/* Send button */}
        <button
          data-testid="send-message-btn"
          onClick={handleSend}
          disabled={!text.trim() || disabled}
          className="flex-shrink-0 p-2.5 transition-all"
          style={{
            background: text.trim() && !disabled ? 'var(--accent)' : 'transparent',
            color: text.trim() && !disabled ? 'var(--accent-text)' : 'var(--text-tertiary)',
            opacity: !text.trim() || disabled ? 0.5 : 1,
          }}
        >
          {disabled ? <Square className="w-5 h-5" /> : <Send className="w-5 h-5" />}
        </button>
      </div>

      {listening && (
        <p className="text-center text-xs mt-2 animate-fade-in" style={{ color: 'var(--accent)' }}>
          Modo Maos Livres ativo - fale agora
        </p>
      )}

      <p className="text-center text-xs mt-2" style={{ color: 'var(--text-tertiary)' }}>
        Kaelum.AI pode cometer erros. Verifique informacoes importantes.
      </p>
    </div>
  );
}
