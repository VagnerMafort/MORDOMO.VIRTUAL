import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { X, Loader2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const STATES = { IDLE: 'idle', LISTENING: 'listening', PROCESSING: 'processing', SPEAKING: 'speaking' };

function AudioVisualizer({ state, volumeRef }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const timeRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    const resize = () => {
      const w = canvas.parentElement.clientWidth;
      const h = canvas.parentElement.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = () => {
      timeRef.current += 0.008;
      const t = timeRef.current;
      const w = canvas.width / (window.devicePixelRatio || 1);
      const h = canvas.height / (window.devicePixelRatio || 1);
      const cx = w / 2;
      const cy = h / 2;
      const vol = volumeRef.current || 0;
      const intensity = Math.min(vol / 80, 1);
      const isActive = state === STATES.LISTENING || state === STATES.SPEAKING;

      ctx.clearRect(0, 0, w, h);

      // Background glow
      const glowSize = 120 + intensity * 80;
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, glowSize);
      if (state === STATES.SPEAKING) {
        grad.addColorStop(0, `rgba(0, 200, 255, ${0.08 + intensity * 0.15})`);
        grad.addColorStop(1, 'rgba(0, 200, 255, 0)');
      } else if (state === STATES.LISTENING) {
        grad.addColorStop(0, `rgba(255, 214, 0, ${0.06 + intensity * 0.2})`);
        grad.addColorStop(1, 'rgba(255, 214, 0, 0)');
      } else {
        grad.addColorStop(0, 'rgba(60, 80, 120, 0.05)');
        grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      }
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // Draw circular spectrum
      const rings = 3;
      for (let r = 0; r < rings; r++) {
        const baseRadius = 50 + r * 30 + (isActive ? intensity * 20 : 0);
        const bars = 64;
        const speed = (r % 2 === 0 ? 1 : -1) * (0.3 + r * 0.15);

        for (let i = 0; i < bars; i++) {
          const angle = (i / bars) * Math.PI * 2 + t * speed;
          const noiseVal = Math.sin(t * 2 + i * 0.5 + r) * 0.5 + 0.5;
          const barHeight = 3 + noiseVal * 15 + (isActive ? intensity * 25 * Math.sin(t * 8 + i * 0.3) : 0);

          const x1 = cx + Math.cos(angle) * baseRadius;
          const y1 = cy + Math.sin(angle) * baseRadius;
          const x2 = cx + Math.cos(angle) * (baseRadius + barHeight);
          const y2 = cy + Math.sin(angle) * (baseRadius + barHeight);

          let alpha = 0.15 + noiseVal * 0.3 + (isActive ? intensity * 0.5 : 0);
          let color;
          if (state === STATES.SPEAKING) {
            color = `rgba(0, ${150 + noiseVal * 105}, 255, ${alpha})`;
          } else if (state === STATES.LISTENING) {
            color = `rgba(255, ${180 + noiseVal * 74}, 0, ${alpha})`;
          } else if (state === STATES.PROCESSING) {
            color = `rgba(100, ${120 + noiseVal * 80}, 255, ${alpha * 0.7})`;
          } else {
            color = `rgba(80, ${100 + noiseVal * 60}, 160, ${alpha * 0.4})`;
          }

          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.5 + (isActive ? intensity : 0);
          ctx.lineCap = 'round';
          ctx.stroke();
        }

        // Inner ring glow
        ctx.beginPath();
        ctx.arc(cx, cy, baseRadius, 0, Math.PI * 2);
        let ringAlpha = 0.05 + (isActive ? intensity * 0.15 : 0);
        if (state === STATES.SPEAKING) ctx.strokeStyle = `rgba(0, 200, 255, ${ringAlpha})`;
        else if (state === STATES.LISTENING) ctx.strokeStyle = `rgba(255, 214, 0, ${ringAlpha})`;
        else ctx.strokeStyle = `rgba(80, 100, 160, ${ringAlpha})`;
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }

      // Center dot
      const dotSize = 3 + (isActive ? intensity * 4 : Math.sin(t) * 1);
      ctx.beginPath();
      ctx.arc(cx, cy, dotSize, 0, Math.PI * 2);
      if (state === STATES.SPEAKING) ctx.fillStyle = `rgba(0, 200, 255, ${0.6 + intensity * 0.4})`;
      else if (state === STATES.LISTENING) ctx.fillStyle = `rgba(255, 214, 0, ${0.5 + intensity * 0.5})`;
      else ctx.fillStyle = 'rgba(80, 100, 160, 0.3)';
      ctx.fill();

      // Floating particles
      for (let i = 0; i < 12; i++) {
        const pa = t * 0.2 + i * (Math.PI * 2 / 12);
        const pr = 130 + Math.sin(t + i * 2) * 30 + (isActive ? intensity * 15 : 0);
        const px = cx + Math.cos(pa) * pr;
        const py = cy + Math.sin(pa) * pr;
        const ps = 1 + Math.sin(t * 2 + i) * 0.5;
        ctx.beginPath();
        ctx.arc(px, py, ps, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(150, 180, 255, ${0.1 + (isActive ? intensity * 0.3 : 0)})`;
        ctx.fill();
      }

      animRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animRef.current);
    };
  }, [state, volumeRef]);

  return <canvas ref={canvasRef} className="absolute inset-0" />;
}

export default function HandsFreeMode({ onClose, agentName }) {
  const { api, getToken } = useAuth();
  const [state, setState] = useState(STATES.IDLE);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [convId, setConvId] = useState(null);
  const [history, setHistory] = useState([]);
  const [debugMsg, setDebugMsg] = useState('');
  const [showDebug, setShowDebug] = useState(false);
  const recognitionRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);
  const autoRestart = useRef(true);
  const volumeRef = useRef(0);
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const volumeLoopRef = useRef(null);
  const streamRef = useRef(null);
  // Refs para evitar stale closures no onend do SpeechRecognition
  const convIdRef = useRef(null);
  const sendMessageRef = useRef(null);
  const startListeningRef = useRef(null);

  const addDebug = useCallback((msg) => {
    console.log('[HandsFree]', msg);
    setDebugMsg(prev => {
      const t = new Date().toLocaleTimeString();
      const line = `${t} · ${msg}`;
      const lines = prev ? prev.split('\n') : [];
      lines.push(line);
      return lines.slice(-8).join('\n');
    });
  }, []);

  // Start volume monitoring
  const startVolumeMonitor = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      audioCtxRef.current = ctx;
      analyserRef.current = analyser;
      const data = new Uint8Array(analyser.frequencyBinCount);
      const loop = () => {
        analyser.getByteFrequencyData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        volumeRef.current = sum / data.length;
        volumeLoopRef.current = requestAnimationFrame(loop);
      };
      loop();
    } catch (e) { console.warn('Audio monitor failed:', e); }
  }, []);

  const stopVolumeMonitor = useCallback(() => {
    cancelAnimationFrame(volumeLoopRef.current);
    streamRef.current?.getTracks().forEach(t => t.stop());
    audioCtxRef.current?.close();
    volumeRef.current = 0;
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.post('/conversations', { title: `[Voz] ${agentName || 'Mordomo Virtual'}` });
        setConvId(data.id);
        convIdRef.current = data.id;
      } catch (e) { console.error(e); }
    })();
    return () => {
      autoRestart.current = false;
      recognitionRef.current?.stop();
      synthRef.current?.cancel();
      stopVolumeMonitor();
    };
  }, [api, agentName, stopVolumeMonitor]);

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      console.error('[HandsFree] Navegador nao suporta Web Speech API');
      return;
    }
    const rec = new SR();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = 'pt-BR';
    rec.onresult = (e) => {
      let final = '', interim = '';
      for (let i = 0; i < e.results.length; i++) {
        if (e.results[i].isFinal) final += e.results[i][0].transcript;
        else interim += e.results[i][0].transcript;
      }
      setTranscript(final || interim);
    };
    rec.onend = () => {
      setTranscript(prev => {
        const text = prev.trim();
        if (text && autoRestart.current && convIdRef.current) {
          // Usa ref pra pegar a versao mais recente (evita stale closure)
          sendMessageRef.current?.(text);
        } else if (autoRestart.current) {
          try { rec.start(); } catch {}
        }
        return prev;
      });
    };
    rec.onerror = (e) => {
      console.warn('[HandsFree] Erro reconhecimento:', e.error);
      if (e.error === 'no-speech' && autoRestart.current) {
        try { rec.start(); } catch {}
      } else if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        alert('Permissao de microfone negada. Autorize o microfone nas configuracoes do navegador e recarregue a pagina.');
        autoRestart.current = false;
      }
    };
    recognitionRef.current = rec;
  }, []);

  const startListening = useCallback(() => {
    synthRef.current?.cancel();
    setTranscript('');
    setResponse('');
    setState(STATES.LISTENING);
    startVolumeMonitor();
    try { recognitionRef.current?.start(); } catch {}
  }, [startVolumeMonitor]);

  // Sincroniza refs para evitar stale closures no onend/onerror do SpeechRecognition
  useEffect(() => { startListeningRef.current = startListening; }, [startListening]);

  const sendMessage = useCallback(async (text) => {
    const cid = convIdRef.current || convId;
    if (!text || !cid) {
      console.warn('[HandsFree] sendMessage: sem texto ou conversa');
      return;
    }
    setState(STATES.PROCESSING);
    setHistory(prev => [...prev, { role: 'user', text }]);
    setTranscript('');
    try {
      const res = await fetch(`${BACKEND_URL}/api/conversations/${cid}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
        body: JSON.stringify({ content: text }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
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
            if (data.type === 'token') { fullContent += data.content; setResponse(fullContent); }
            else if (data.type === 'done') {
              setHistory(prev => [...prev, { role: 'assistant', text: fullContent }]);
              speakResponse(fullContent);
            }
          } catch {}
        }
      }
      // Fallback: se o backend terminou mas nao enviou evento 'done', fala mesmo assim
      if (fullContent && state !== STATES.SPEAKING) {
        setHistory(prev => {
          if (prev[prev.length - 1]?.role !== 'assistant') {
            return [...prev, { role: 'assistant', text: fullContent }];
          }
          return prev;
        });
        speakResponse(fullContent);
      }
    } catch (e) {
      console.error('[HandsFree] Erro ao enviar:', e);
      setState(STATES.IDLE);
      if (autoRestart.current) setTimeout(() => startListeningRef.current?.(), 800);
    }
  }, [convId, getToken, state]);

  // Sincroniza ref de sendMessage
  useEffect(() => { sendMessageRef.current = sendMessage; }, [sendMessage]);

  const speakResponse = useCallback((text) => {
    setState(STATES.SPEAKING);
    addDebug(`TTS start: ${text.length} chars`);
    const clean = text.replace(/```[\s\S]*?```/g, '').replace(/`[^`]+`/g, '')
      .replace(/\*\*(.+?)\*\*/g, '$1').replace(/\*(.+?)\*/g, '$1')
      .replace(/#{1,3}\s/g, '').replace(/\[SKILL:[^\]]+\][^`]*/g, '')
      .replace(/https?:\/\/\S+/g, '').trim();
    if (!clean) {
      addDebug('TTS: texto vazio apos limpar');
      setState(STATES.IDLE);
      if (autoRestart.current) setTimeout(() => startListeningRef.current?.(), 500);
      return;
    }

    const synth = window.speechSynthesis;
    if (!synth) {
      addDebug('ERRO: speechSynthesis nao suportado');
      setState(STATES.IDLE);
      if (autoRestart.current) setTimeout(() => startListeningRef.current?.(), 500);
      return;
    }

    // Garantir que nada esta em fila
    synth.cancel();

    // SAFETY NET: se travar, forca retorno a IDLE apos 45s
    let hardTimeoutId = null;
    let finished = false;
    const finishOnce = (reason) => {
      if (finished) return;
      finished = true;
      if (hardTimeoutId) clearTimeout(hardTimeoutId);
      addDebug(`TTS fim: ${reason}`);
      try { synth.cancel(); } catch {}
      setState(STATES.IDLE);
      if (autoRestart.current) setTimeout(() => startListeningRef.current?.(), 300);
    };
    hardTimeoutId = setTimeout(() => finishOnce('timeout-45s'), 45000);

    const doSpeak = () => {
      const voices = synth.getVoices();
      addDebug(`${voices.length} vozes disponiveis`);
      const ptVoice = voices.find(v => v.lang && v.lang.toLowerCase().startsWith('pt'))
        || voices.find(v => v.default)
        || voices[0];

      if (ptVoice) {
        addDebug(`Voz: ${ptVoice.name} (${ptVoice.lang})`);
      } else {
        addDebug('AVISO: nenhuma voz encontrada');
        finishOnce('no-voices');
        return;
      }

      // Chrome tem limite ~200 chars por utterance — quebra em pedacos
      const textToSpeak = clean.slice(0, 800);
      const chunks = [];
      const sentences = textToSpeak.match(/[^.!?]+[.!?]*\s*/g) || [textToSpeak];
      let current = '';
      for (const s of sentences) {
        if ((current + s).length > 200) {
          if (current) chunks.push(current.trim());
          current = s;
        } else {
          current += s;
        }
      }
      if (current.trim()) chunks.push(current.trim());
      if (chunks.length === 0) chunks.push(textToSpeak);

      let idx = 0;
      const speakNext = () => {
        if (finished) return;
        if (idx >= chunks.length) {
          finishOnce('done');
          return;
        }
        const utt = new SpeechSynthesisUtterance(chunks[idx]);
        if (ptVoice) utt.voice = ptVoice;
        utt.lang = (ptVoice && ptVoice.lang) || 'pt-BR';
        utt.rate = 1.05;
        utt.pitch = 1;
        utt.volume = 1;

        // Timeout por chunk (alguns TTS nao disparam onend)
        const chunkTimeout = setTimeout(() => {
          console.warn('[HandsFree] chunk timeout, pulando');
          idx++;
          speakNext();
        }, Math.max(5000, chunks[idx].length * 100));

        utt.onend = () => {
          clearTimeout(chunkTimeout);
          idx++;
          speakNext();
        };
        utt.onerror = (e) => {
          console.warn('[HandsFree] TTS erro:', e.error || e);
          clearTimeout(chunkTimeout);
          idx++;
          speakNext();
        };
        try {
          synth.speak(utt);
          // Workaround do bug do Chrome que pausa TTS apos ~15s
          setTimeout(() => { if (synth.speaking) { try { synth.pause(); synth.resume(); } catch {} } }, 10000);
        } catch (err) {
          console.error('[HandsFree] Falha ao falar:', err);
          clearTimeout(chunkTimeout);
          idx++;
          speakNext();
        }
      };
      // Pequeno delay pro Chrome liberar o audio do microfone
      setTimeout(speakNext, 250);
    };

    // Garante que as vozes foram carregadas
    if (synth.getVoices().length === 0) {
      const onVoices = () => {
        synth.removeEventListener('voiceschanged', onVoices);
        doSpeak();
      };
      synth.addEventListener('voiceschanged', onVoices);
      // Fallback: se nao disparar em 1s, tenta mesmo assim
      setTimeout(() => { synth.removeEventListener('voiceschanged', onVoices); doSpeak(); }, 1000);
    } else {
      doSpeak();
    }
  }, [addDebug]);

  const toggleMode = () => {
    if (state === STATES.IDLE) { autoRestart.current = true; startListening(); }
    else { autoRestart.current = false; recognitionRef.current?.stop(); synthRef.current?.cancel(); stopVolumeMonitor(); setState(STATES.IDLE); }
  };

  const handleClose = () => {
    autoRestart.current = false;
    recognitionRef.current?.stop();
    synthRef.current?.cancel();
    stopVolumeMonitor();
    onClose();
  };

  const stateLabels = {
    [STATES.IDLE]: 'Toque para ativar',
    [STATES.LISTENING]: 'Ouvindo...',
    [STATES.PROCESSING]: 'Processando...',
    [STATES.SPEAKING]: 'Respondendo...',
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col" style={{ background: '#020810' }}>
      {/* Visualizer */}
      <div className="absolute inset-0">
        <AudioVisualizer state={state} volumeRef={volumeRef} />
      </div>

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between px-6 py-4">
        <div>
          <h2 className="text-lg font-black tracking-tighter" style={{ fontFamily: 'Outfit', color: 'rgba(255,255,255,0.9)' }}>
            Mordomo Virtual
          </h2>
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
            {agentName || 'Assistente AI'} &middot; Modo Voz
          </p>
        </div>
        <button data-testid="close-handsfree-btn" onClick={handleClose}
          className="p-2 transition-opacity" style={{ color: 'rgba(255,255,255,0.4)' }}>
          <X className="w-6 h-6" />
        </button>
      </div>

      {/* Debug toggle */}
      <button
        data-testid="handsfree-debug-toggle"
        onClick={() => setShowDebug(s => !s)}
        className="absolute top-4 left-4 z-20 text-xs px-2 py-1 rounded"
        style={{ color: 'rgba(255,255,255,0.3)', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        {showDebug ? 'Ocultar' : 'Debug'}
      </button>
      {showDebug && debugMsg && (
        <div className="absolute top-14 left-4 z-20 p-3 rounded max-w-md text-xs font-mono whitespace-pre-line"
          style={{ background: 'rgba(0,0,0,0.7)', color: 'rgba(180,220,255,0.9)', border: '1px solid rgba(255,255,255,0.1)' }}>
          {debugMsg}
        </div>
      )}

      {/* Center content */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-6">
        {/* History */}
        <div className="w-full max-w-md mb-8 flex flex-col gap-3">
          {history.slice(-4).map((h, i) => (
            <div key={i} className="animate-fade-in">
              <p className="text-xs font-medium mb-0.5" style={{
                fontFamily: 'Outfit',
                color: h.role === 'user' ? 'rgba(255,255,255,0.3)' : 'rgba(0,200,255,0.8)',
              }}>
                {h.role === 'user' ? 'Voce' : agentName || 'Mordomo'}
              </p>
              <p className="text-sm leading-relaxed" style={{
                color: h.role === 'user' ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.85)',
              }}>
                {h.text.length > 150 ? h.text.slice(0, 150) + '...' : h.text}
              </p>
            </div>
          ))}
        </div>

        {/* Tap area */}
        <button data-testid="handsfree-mic-btn" onClick={toggleMode}
          className="w-32 h-32 rounded-full flex items-center justify-center transition-all"
          style={{ background: 'transparent', cursor: 'pointer' }}>
          {state === STATES.PROCESSING && <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'rgba(100,150,255,0.7)' }} />}
        </button>

        {/* State label */}
        <p className="mt-4 text-sm font-medium tracking-wide" style={{
          fontFamily: 'Outfit',
          color: state === STATES.LISTENING ? 'rgba(255,214,0,0.9)'
            : state === STATES.SPEAKING ? 'rgba(0,200,255,0.9)'
            : state === STATES.PROCESSING ? 'rgba(100,150,255,0.7)'
            : 'rgba(255,255,255,0.3)',
        }}>
          {stateLabels[state]}
        </p>

        {/* Live transcript */}
        {transcript && state === STATES.LISTENING && (
          <p className="mt-4 text-lg text-center animate-fade-in max-w-md" style={{ color: 'rgba(255,255,255,0.9)' }}>
            "{transcript}"
          </p>
        )}
        {response && (state === STATES.PROCESSING || state === STATES.SPEAKING) && (
          <p className="mt-4 text-sm text-center max-w-md leading-relaxed animate-fade-in" style={{ color: 'rgba(255,255,255,0.6)' }}>
            {response.length > 250 ? response.slice(0, 250) + '...' : response}
          </p>
        )}
      </div>

      {/* Footer */}
      <div className="relative z-10 px-6 py-4 text-center">
        <p className="text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>
          {state === STATES.IDLE ? 'Toque no centro para iniciar' :
           state === STATES.LISTENING ? 'Fale agora — envio automatico ao pausar' :
           state === STATES.SPEAKING ? 'Ouvindo resposta — volta a escutar automaticamente' :
           'Processando...'}
        </p>
      </div>
    </div>
  );
}
