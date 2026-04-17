import React, { useEffect, useRef } from 'react';

// Simple orb visualizer that reacts to state and volume
export default function AudioVisualizer({ state, volumeRef }) {
  const canvasRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    const resize = () => {
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener('resize', resize);

    let t = 0;
    const render = () => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h / 2;
      const vol = volumeRef?.current || 0;

      // Color based on state
      const colors = {
        idle: ['rgba(59,130,246,0.4)', 'rgba(59,130,246,0.05)'],
        listening: ['rgba(34,211,238,0.7)', 'rgba(34,211,238,0.1)'],
        processing: ['rgba(250,204,21,0.7)', 'rgba(250,204,21,0.1)'],
        speaking: ['rgba(168,85,247,0.7)', 'rgba(168,85,247,0.1)'],
      };
      const [c1, c2] = colors[state] || colors.idle;

      const baseR = Math.min(w, h) * 0.18;
      const pulse = Math.sin(t / 30) * 10;
      const volBoost = Math.min(vol * 1.5, 60);
      const r = baseR + pulse + volBoost;

      // Outer glow
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 2.2);
      grad.addColorStop(0, c1);
      grad.addColorStop(1, c2);
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(cx, cy, r * 2.2, 0, Math.PI * 2);
      ctx.fill();

      // Core orb
      ctx.fillStyle = c1;
      ctx.beginPath();
      ctx.arc(cx, cy, r * 0.6, 0, Math.PI * 2);
      ctx.fill();

      t += 1;
      rafRef.current = requestAnimationFrame(render);
    };
    render();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(rafRef.current);
    };
  }, [state, volumeRef]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full"
      style={{ pointerEvents: 'none' }}
    />
  );
}
