import React, { useEffect, useRef, useState, useCallback } from 'react';
import { X, Mic } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import AudioVisualizer from './AudioVisualizer';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const STATES = { IDLE: 'idle', LISTENING: 'listening', PROCESSING: 'processing', SPEAKING: 'speaking' };

const LABELS = {
  idle: 'Toque para falar',
  listening: 'Ouvindo...',
  processing: 'Transcrevendo + respondendo...',
  speaking: 'Respondendo...',
};

// Duracao maxima de gravacao por turno (ms)
const MAX_RECORDING_MS = 30000;
// Silencio para parar (ms) - detectado via analise de volume
const SILENCE_MS = 1500;
// Volume minimo pra considerar fala
const VOLUME_THRESHOLD = 12;

export default function HandsFreeMode({ onClose, agentName }) {
  const { api, getToken } = useAuth();
  const [state, setState] = useState(STATES.IDLE);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [convId, setConvId] = useState(null);
  const [history, setHistory] = useState([]);
  const [debugMsg, setDebugMsg] = useState('');
  const [showDebug, setShowDebug] = useState(false);

  const convIdRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const volumeRef = useRef(0);
  const volumeLoopRef = useRef(null);
  const autoRestart = useRef(true);
  const currentAudioRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const recordStartRef = useRef(0);
  const hasSpokenRef = useRef(false);

  const addDebug = useCallback((msg) => {
    console.log('[Voice]', msg);
    setDebugMsg(prev => {
      const t = new Date().toLocaleTimeString();
      const lines = prev ? prev.split('\n') : [];
      lines.push(`${t} ${msg}`);
      return lines.slice(-10).join('\n');
    });
  }, []);

  // Cria conversa ao montar
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.post('/conversations', { title: `[Voz] ${agentName || 'Mordomo Virtual'}` });
        setConvId(data.id);
        convIdRef.current = data.id;
        addDebug(`Conversa criada`);
      } catch (e) {
        addDebug(`Erro ao criar conversa: ${e.message}`);
      }
    })();
    return () => {
      autoRestart.current = false;
      stopRecording();
      if (currentAudioRef.current) {
        try { currentAudioRef.current.pause(); currentAudioRef.current.src = ''; } catch {}
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, agentName]);

  // Visualizador de volume
  const startAudioAnalysis = useCallback((stream) => {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
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

        // Deteccao de silencio apos voz detectada
        if (state === STATES.LISTENING) {
          if (vol > VOLUME_THRESHOLD) {
            hasSpokenRef.current = true;
            if (silenceTimerRef.current) {
              clearTimeout(silenceTimerRef.current);
              silenceTimerRef.current = null;
            }
          } else if (hasSpokenRef.current && !silenceTimerRef.current) {
            silenceTimerRef.current = setTimeout(() => {
              addDebug('Silencio detectado, parando gravacao');
              stopRecording();
            }, SILENCE_MS);
          }
        }
        volumeLoopRef.current = requestAnimationFrame(loop);
      };
      loop();
    } catch (e) {
      addDebug(`Erro analyser: ${e.message}`);
    }
  }, [state, addDebug]);

  const stopAudioAnalysis = useCallback(() => {
    cancelAnimationFrame(volumeLoopRef.current);
    if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
    try { audioCtxRef.current?.close(); } catch {}
    audioCtxRef.current = null;
    analyserRef.current = null;
    volumeRef.current = 0;
  }, []);

  const stopRecording = useCallback(() => {
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
    } catch {}
    try { streamRef.current?.getTracks().forEach(t => t.stop()); } catch {}
    streamRef.current = null;
    stopAudioAnalysis();
  }, [stopAudioAnalysis]);

  const transcribeAudio = useCallback(async (audioBlob) => {
    setState(STATES.PROCESSING);
    addDebug(`Transcrevendo ${audioBlob.size} bytes`);
    try {
      const form = new FormData();
      form.append('file', audioBlob, 'audio.webm');
      const res = await fetch(`${BACKEND_URL}/api/voice/transcribe?language=pt`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
        body: form,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const text = (data.text || '').trim();
      addDebug(`Transcrito: "${text.slice(0, 40)}..."`);
      return text;
    } catch (e) {
      addDebug(`Erro transcribe: ${e.message}`);
      return '';
    }
  }, [getToken, addDebug]);

  const playAudioFromServer = useCallback(async (text) => {
    return new Promise((resolve) => {
      addDebug(`Sintetizando ${text.length} chars`);
      const url = `${BACKEND_URL}/api/voice/speak?text=${encodeURIComponent(text)}`;
      fetch(url, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
        .then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.blob();
        })
        .then(blob => {
          const audioUrl = URL.createObjectURL(blob);
          const audio = new Audio(audioUrl);
          currentAudioRef.current = audio;
          audio.playbackRate = 1.05;
          audio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            addDebug('Audio terminou');
            resolve();
          };
          audio.onerror = (e) => {
            addDebug(`Erro play: ${e}`);
            URL.revokeObjectURL(audioUrl);
            resolve();
          };
          audio.play().catch(err => {
            addDebug(`Play bloqueado: ${err.message}`);
            resolve();
          });
        })
        .catch(err => {
          addDebug(`Erro TTS: ${err.message}`);
          resolve();
        });
    });
  }, [getToken, addDebug]);

  const sendMessage = useCallback(async (text) => {
    const cid = convIdRef.current;
    if (!text || !cid) return;
    setHistory(prev => [...prev, { role: 'user', text }]);
    setTranscript('');
    setResponse('');
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
            if (data.type === 'token') {
              fullContent += data.content;
              setResponse(fullContent);
            }
          } catch {}
        }
      }
      setHistory(prev => [...prev, { role: 'assistant', text: fullContent }]);

      // Limpa markdown/urls antes de falar
      const clean = fullContent
        .replace(/```[\s\S]*?```/g, '').replace(/`[^`]+`/g, '')
        .replace(/\*\*(.+?)\*\*/g, '$1').replace(/\*(.+?)\*/g, '$1')
        .replace(/#{1,3}\s/g, '').replace(/\[SKILL:[^\]]+\][^`]*/g, '')
        .replace(/https?:\/\/\S+/g, '').trim();

      if (clean) {
        setState(STATES.SPEAKING);
        await playAudioFromServer(clean);
      }
    } catch (e) {
      addDebug(`Erro chat: ${e.message}`);
    } finally {
      setState(STATES.IDLE);
      if (autoRestart.current) setTimeout(() => startListening(), 150);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [convId, getToken, playAudioFromServer, addDebug]);

  const startListening = useCallback(async () => {
    if (state === STATES.LISTENING || state === STATES.PROCESSING || state === STATES.SPEAKING) return;
    setTranscript('');
    setResponse('');
    hasSpokenRef.current = false;
    addDebug('Iniciando gravacao');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      });
      streamRef.current = stream;
      audioChunksRef.current = [];

      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '');
      const mr = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      mediaRecorderRef.current = mr;

      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mr.onstop = async () => {
        stopAudioAnalysis();
        try { streamRef.current?.getTracks().forEach(t => t.stop()); } catch {}
        streamRef.current = null;

        if (!hasSpokenRef.current) {
          addDebug('Nao houve fala detectada, reiniciando');
          setState(STATES.IDLE);
          if (autoRestart.current) setTimeout(() => startListening(), 200);
          return;
        }

        const blob = new Blob(audioChunksRef.current, { type: mime || 'audio/webm' });
        if (blob.size < 1000) {
          addDebug('Audio muito pequeno, reiniciando');
          setState(STATES.IDLE);
          if (autoRestart.current) setTimeout(() => startListening(), 200);
          return;
        }
        const text = await transcribeAudio(blob);
        if (text.length < 2) {
          addDebug('Transcricao vazia, reiniciando');
          setState(STATES.IDLE);
          if (autoRestart.current) setTimeout(() => startListening(), 200);
          return;
        }
        setTranscript(text);
        await sendMessage(text);
      };

      mr.start(500);
      recordStartRef.current = Date.now();
      setState(STATES.LISTENING);
      startAudioAnalysis(stream);

      // Timeout absoluto
      setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording' &&
            Date.now() - recordStartRef.current >= MAX_RECORDING_MS) {
          addDebug('Tempo maximo atingido');
          stopRecording();
        }
      }, MAX_RECORDING_MS + 100);
    } catch (e) {
      addDebug(`Erro mic: ${e.message}`);
      setState(STATES.IDLE);
      alert('Permissao de microfone negada ou indisponivel. Autorize nas configuracoes do navegador.');
    }
  }, [state, startAudioAnalysis, stopAudioAnalysis, stopRecording, transcribeAudio, sendMessage, addDebug]);

  const handleCenterTap = () => {
    if (state === STATES.IDLE) {
      autoRestart.current = true;
      startListening();
    } else if (state === STATES.LISTENING) {
      stopRecording();
    } else if (state === STATES.SPEAKING && currentAudioRef.current) {
      try { currentAudioRef.current.pause(); } catch {}
      setState(STATES.IDLE);
      if (autoRestart.current) setTimeout(() => startListening(), 100);
    }
  };

  const handleClose = () => {
    autoRestart.current = false;
    stopRecording();
    if (currentAudioRef.current) {
      try { currentAudioRef.current.pause(); currentAudioRef.current.src = ''; } catch {}
    }
    onClose?.();
  };

  return (
    <div data-testid="handsfree-mode" className="fixed inset-0 z-50 flex flex-col" style={{ background: '#020810' }}>
      <div className="absolute inset-0">
        <AudioVisualizer state={state} volumeRef={volumeRef} />
      </div>

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between px-6 py-4">
        <div className="ml-20">
          <h2 className="text-white text-lg font-medium">Modo Voz</h2>
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.5)' }}>
            {agentName || 'Mordomo Virtual'} · 100% local
          </p>
        </div>
        <button data-testid="close-handsfree-btn" onClick={handleClose}
          className="p-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
          <X className="w-6 h-6" />
        </button>
      </div>

      {/* Debug toggle */}
      <button
        data-testid="handsfree-debug-toggle"
        onClick={() => setShowDebug(s => !s)}
        className="absolute top-4 left-4 z-30 text-xs px-3 py-1.5 rounded font-medium"
        style={{
          color: showDebug ? '#fff' : 'rgba(255,255,255,0.7)',
          background: showDebug ? 'rgba(59,130,246,0.8)' : 'rgba(255,255,255,0.1)',
          border: '1px solid rgba(255,255,255,0.2)'
        }}
      >
        {showDebug ? 'Fechar Debug' : 'Debug'}
      </button>
      {showDebug && (
        <div className="absolute top-14 left-4 z-30 p-3 rounded max-w-md text-xs font-mono whitespace-pre-line"
          style={{ background: 'rgba(0,0,0,0.85)', color: 'rgba(180,220,255,0.95)', border: '1px solid rgba(255,255,255,0.2)' }}>
          <div className="mb-2 opacity-70">Estado: <b>{state}</b></div>
          <div>{debugMsg || '(sem logs ainda)'}</div>
        </div>
      )}

      {/* Bottom: transcript, response, tap area */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-end pb-10 px-6">
        {transcript && (
          <div className="text-white/80 text-sm mb-4 max-w-xl text-center">
            <span className="opacity-50">Voce: </span>{transcript}
          </div>
        )}
        {response && (
          <div className="text-white text-base mb-6 max-w-xl text-center">
            {response}
          </div>
        )}

        <button
          data-testid="handsfree-center-tap"
          onClick={handleCenterTap}
          className="w-20 h-20 rounded-full flex items-center justify-center mb-4 transition"
          style={{
            background: state === STATES.LISTENING ? 'rgba(239,68,68,0.9)' : 'rgba(59,130,246,0.9)',
            boxShadow: '0 0 40px rgba(59,130,246,0.4)'
          }}
        >
          <Mic className="w-8 h-8 text-white" />
        </button>

        <p className="text-white/60 text-sm">{LABELS[state]}</p>
      </div>
    </div>
  );
}
