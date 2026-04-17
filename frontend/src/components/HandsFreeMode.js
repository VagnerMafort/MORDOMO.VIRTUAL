import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { X, Loader2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const STATES = { IDLE: 'idle', LISTENING: 'listening', PROCESSING: 'processing', SPEAKING: 'speaking' };
const SILENCE_MS = 1200;
const VOLUME_THRESHOLD = 12;
const MAX_RECORDING_MS = 30000;

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

        ctx.beginPath();
        ctx.arc(cx, cy, baseRadius, 0, Math.PI * 2);
        ctx.strokeStyle = state === STATES.SPEAKING
          ? `rgba(0, 200, 255, ${0.1 + intensity * 0.2})`
          : state === STATES.LISTENING
          ? `rgba(255, 214, 0, ${0.1 + intensity * 0.2})`
          : 'rgba(80, 100, 160, 0.06)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      animRef.current = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animRef.current);
    };
  }, [state, volumeRef]);

  return <canvas ref={canvasRef} style={{ display: 'block' }} />;
}

export default function HandsFreeMode({ onClose, agentName }) {
  const { api, getToken } = useAuth();
  const [state, setState] = useState(STATES.IDLE);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [convId, setConvId] = useState(null);
  const [history, setHistory] = useState([]);

  const convIdRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const volumeRef = useRef(0);
  const volumeLoopRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const hasSpokenRef = useRef(false);
  const currentAudioRef = useRef(null);
  const autoRestart = useRef(true);
  const recordStartRef = useRef(0);
  const startListeningRef = useRef(null);

  // Cria conversa ao montar
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
      cleanupRecording();
      if (currentAudioRef.current) {
        try { currentAudioRef.current.pause(); currentAudioRef.current.src = ''; } catch {}
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, agentName]);

  const cleanupRecording = useCallback(() => {
    cancelAnimationFrame(volumeLoopRef.current);
    if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
    try { if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop(); } catch {}
    try { streamRef.current?.getTracks().forEach(t => t.stop()); } catch {}
    try { audioCtxRef.current?.close(); } catch {}
    streamRef.current = null;
    audioCtxRef.current = null;
    analyserRef.current = null;
    volumeRef.current = 0;
  }, []);

  const stopRecording = useCallback(() => {
    try {
      if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop();
    } catch {}
  }, []);

  const transcribeAudio = useCallback(async (blob) => {
    const form = new FormData();
    form.append('file', blob, 'audio.webm');
    const res = await fetch(`${BACKEND_URL}/api/voice/transcribe?language=pt`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getToken()}` },
      body: form,
    });
    if (!res.ok) throw new Error(`Transcribe HTTP ${res.status}`);
    const data = await res.json();
    return (data.text || '').trim();
  }, [getToken]);

  const playTTS = useCallback(async (text) => {
    return new Promise((resolve) => {
      const url = `${BACKEND_URL}/api/voice/speak?text=${encodeURIComponent(text)}`;
      fetch(url, { method: 'POST', headers: { 'Authorization': `Bearer ${getToken()}` } })
        .then(r => r.ok ? r.blob() : Promise.reject(new Error(`TTS ${r.status}`)))
        .then(blob => {
          const audioUrl = URL.createObjectURL(blob);
          const audio = new Audio(audioUrl);
          currentAudioRef.current = audio;
          audio.playbackRate = 1.0;
          audio.onended = () => { URL.revokeObjectURL(audioUrl); resolve(); };
          audio.onerror = () => { URL.revokeObjectURL(audioUrl); resolve(); };
          audio.play().catch(() => resolve());
        })
        .catch(err => { console.warn('[Voice] TTS err:', err); resolve(); });
    });
  }, [getToken]);

  const sendMessage = useCallback(async (text) => {
    const cid = convIdRef.current;
    if (!text || !cid) return;
    setState(STATES.PROCESSING);
    setHistory(prev => [...prev, { role: 'user', text }]);
    setResponse('');
    try {
      const res = await fetch(`${BACKEND_URL}/api/conversations/${cid}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
        body: JSON.stringify({ content: text }),
      });
      if (!res.ok) throw new Error(`Chat HTTP ${res.status}`);
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
          } catch {}
        }
      }
      setHistory(prev => [...prev, { role: 'assistant', text: fullContent }]);
      const clean = fullContent
        .replace(/```[\s\S]*?```/g, '').replace(/`[^`]+`/g, '')
        .replace(/\*\*(.+?)\*\*/g, '$1').replace(/\*(.+?)\*/g, '$1')
        .replace(/#{1,3}\s/g, '').replace(/\[SKILL:[^\]]+\][^`]*/g, '')
        .replace(/https?:\/\/\S+/g, '').trim();
      if (clean) {
        setState(STATES.SPEAKING);
        await playTTS(clean);
      }
    } catch (e) {
      console.error('[Voice] chat err:', e);
    } finally {
      setState(STATES.IDLE);
      if (autoRestart.current) setTimeout(() => startListeningRef.current?.(), 100);
    }
  }, [getToken, playTTS]);

  const startListening = useCallback(async () => {
    if (state === STATES.PROCESSING || state === STATES.SPEAKING) return;
    setTranscript('');
    setResponse('');
    hasSpokenRef.current = false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      streamRef.current = stream;
      audioChunksRef.current = [];

      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '');
      const mr = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      mediaRecorderRef.current = mr;

      mr.ondataavailable = (e) => { if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data); };
      mr.onstop = async () => {
        try { streamRef.current?.getTracks().forEach(t => t.stop()); } catch {}
        try { audioCtxRef.current?.close(); } catch {}
        cancelAnimationFrame(volumeLoopRef.current);
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
        volumeRef.current = 0;

        if (!hasSpokenRef.current) {
          setState(STATES.IDLE);
          if (autoRestart.current) setTimeout(() => startListeningRef.current?.(), 200);
          return;
        }
        const blob = new Blob(audioChunksRef.current, { type: mime || 'audio/webm' });
        if (blob.size < 1500) {
          setState(STATES.IDLE);
          if (autoRestart.current) setTimeout(() => startListeningRef.current?.(), 200);
          return;
        }
        setState(STATES.PROCESSING);
        try {
          const text = await transcribeAudio(blob);
          if (text.length < 2) {
            setState(STATES.IDLE);
            if (autoRestart.current) setTimeout(() => startListeningRef.current?.(), 200);
            return;
          }
          setTranscript(text);
          await sendMessage(text);
        } catch (e) {
          console.error('[Voice] transcribe err:', e);
          setState(STATES.IDLE);
          if (autoRestart.current) setTimeout(() => startListeningRef.current?.(), 300);
        }
      };

      mr.start(500);
      recordStartRef.current = Date.now();
      setState(STATES.LISTENING);

      // Volume monitor + silence detection
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      src.connect(analyser);
      audioCtxRef.current = ctx;
      analyserRef.current = analyser;
      const data = new Uint8Array(analyser.frequencyBinCount);
      const loop = () => {
        if (!analyserRef.current) return;
        analyser.getByteFrequencyData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        const vol = sum / data.length;
        volumeRef.current = vol;

        if (vol > VOLUME_THRESHOLD) {
          hasSpokenRef.current = true;
          if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
        } else if (hasSpokenRef.current && !silenceTimerRef.current) {
          silenceTimerRef.current = setTimeout(() => { stopRecording(); }, SILENCE_MS);
        }
        volumeLoopRef.current = requestAnimationFrame(loop);
      };
      loop();

      // Timeout absoluto
      setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording' &&
            Date.now() - recordStartRef.current >= MAX_RECORDING_MS) {
          stopRecording();
        }
      }, MAX_RECORDING_MS + 100);
    } catch (e) {
      console.error('[Voice] mic err:', e);
      setState(STATES.IDLE);
      alert('Nao foi possivel acessar o microfone. Autorize o microfone e tente novamente.');
    }
  }, [state, transcribeAudio, sendMessage, stopRecording]);

  useEffect(() => { startListeningRef.current = startListening; }, [startListening]);

  const toggleMode = () => {
    if (state === STATES.IDLE) {
      autoRestart.current = true;
      startListening();
    } else {
      autoRestart.current = false;
      cleanupRecording();
      if (currentAudioRef.current) { try { currentAudioRef.current.pause(); } catch {} }
      setState(STATES.IDLE);
    }
  };

  const handleClose = () => {
    autoRestart.current = false;
    cleanupRecording();
    if (currentAudioRef.current) {
      try { currentAudioRef.current.pause(); currentAudioRef.current.src = ''; } catch {}
    }
    onClose?.();
  };

  const stateLabels = {
    [STATES.IDLE]: 'Toque para ativar',
    [STATES.LISTENING]: 'Ouvindo...',
    [STATES.PROCESSING]: 'Processando...',
    [STATES.SPEAKING]: 'Respondendo...',
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col" style={{ background: '#020810' }}>
      <div className="absolute inset-0">
        <AudioVisualizer state={state} volumeRef={volumeRef} />
      </div>

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

      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-6">
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

        <button data-testid="handsfree-mic-btn" onClick={toggleMode}
          className="w-32 h-32 rounded-full flex items-center justify-center transition-all"
          style={{ background: 'transparent', cursor: 'pointer' }}>
          {state === STATES.PROCESSING && <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'rgba(100,150,255,0.7)' }} />}
        </button>

        <p className="mt-4 text-sm font-medium tracking-wide" style={{
          fontFamily: 'Outfit',
          color: state === STATES.LISTENING ? 'rgba(255,214,0,0.9)'
            : state === STATES.SPEAKING ? 'rgba(0,200,255,0.9)'
            : state === STATES.PROCESSING ? 'rgba(100,150,255,0.7)'
            : 'rgba(255,255,255,0.3)',
        }}>
          {stateLabels[state]}
        </p>

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
