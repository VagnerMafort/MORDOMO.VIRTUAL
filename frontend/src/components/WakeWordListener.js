import { useEffect, useRef, useState, useCallback } from 'react';

export default function WakeWordListener({ agentName, enabled, onActivated }) {
  const [status, setStatus] = useState('off'); // off, listening, detected
  const recognitionRef = useRef(null);
  const restartTimer = useRef(null);
  const enabledRef = useRef(enabled);

  useEffect(() => { enabledRef.current = enabled; }, [enabled]);

  const wakePhrase = (agentName || 'Mordomo').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

  const startPassiveListening = useCallback(() => {
    if (!enabledRef.current || !recognitionRef.current) return;
    try {
      recognitionRef.current.start();
      setStatus('listening');
    } catch (e) {
      // Already started, ignore
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      recognitionRef.current?.stop();
      setStatus('off');
      return;
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;

    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = 'pt-BR';
    rec.maxAlternatives = 3;

    rec.onresult = (e) => {
      for (let i = e.resultIndex; i < e.results.length; i++) {
        for (let j = 0; j < e.results[i].length; j++) {
          const text = e.results[i][j].transcript.toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '');

          // Check for wake word variations
          const triggers = [
            `hey ${wakePhrase}`,
            `ei ${wakePhrase}`,
            `oi ${wakePhrase}`,
            `hei ${wakePhrase}`,
            `e ${wakePhrase}`,
          ];

          const detected = triggers.some(t => text.includes(t));
          if (detected) {
            setStatus('detected');
            rec.stop();
            clearTimeout(restartTimer.current);
            onActivated();
            return;
          }
        }
      }
    };

    rec.onend = () => {
      if (enabledRef.current && status !== 'detected') {
        // Restart after a brief pause to avoid overloading
        restartTimer.current = setTimeout(() => {
          if (enabledRef.current) {
            try { rec.start(); setStatus('listening'); } catch {}
          }
        }, 300);
      }
    };

    rec.onerror = (e) => {
      if (e.error === 'no-speech' || e.error === 'aborted') {
        // Normal - just restart
        if (enabledRef.current) {
          restartTimer.current = setTimeout(() => {
            try { rec.start(); setStatus('listening'); } catch {}
          }, 500);
        }
      } else {
        console.warn('Wake word error:', e.error);
        setStatus('off');
      }
    };

    recognitionRef.current = rec;
    startPassiveListening();

    return () => {
      enabledRef.current = false;
      clearTimeout(restartTimer.current);
      try { rec.stop(); } catch {}
      setStatus('off');
    };
  }, [enabled, wakePhrase, onActivated, startPassiveListening]);

  // Reset after hands-free closes
  useEffect(() => {
    if (enabled && status === 'detected') {
      const timer = setTimeout(() => {
        setStatus('listening');
        startPassiveListening();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [enabled, status, startPassiveListening]);

  if (!enabled) return null;

  return (
    <div
      data-testid="wake-word-indicator"
      className="fixed bottom-6 left-6 z-20 flex items-center gap-2 px-3 py-2 transition-all"
      style={{
        background: status === 'detected' ? 'var(--accent)' : 'var(--bg-surface)',
        border: `1px solid ${status === 'listening' ? 'var(--success)' : 'var(--border-subtle)'}`,
        opacity: 0.9,
      }}
    >
      <span
        className="w-2 h-2 rounded-full flex-shrink-0"
        style={{
          background: status === 'listening' ? 'var(--success)' : status === 'detected' ? 'var(--accent-text)' : 'var(--text-tertiary)',
          animation: status === 'listening' ? 'pulse-ring 2s infinite' : 'none',
        }}
      />
      <span className="text-xs font-mono" style={{
        color: status === 'detected' ? 'var(--accent-text)' : 'var(--text-tertiary)',
      }}>
        {status === 'listening' ? `"Hey ${agentName || 'Mordomo'}"` :
         status === 'detected' ? 'Ativado!' : 'Off'}
      </span>
    </div>
  );
}
