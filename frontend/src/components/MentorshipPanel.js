import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  X, ArrowLeft, Plus, Trash2, Upload, FileText, Loader2,
  BookOpen, Download, Eye, ChevronDown, ChevronUp, GraduationCap
} from 'lucide-react';
import MentorshipEditor from '@/components/MentorshipEditor';
import { toast } from 'sonner';

function formatContent(text) {
  if (!text) return '';
  return text
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/\n/g, '<br/>');
}

export default function MentorshipPanel({ onClose }) {
  const { api } = useAuth();
  const [tab, setTab] = useState('create');
  const [mentorships, setMentorships] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [viewing, setViewing] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState({ title: '', knowledge_text: '', niche: '', target_audience: '', duration_weeks: 8 });
  const fileRef = useRef(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [m, k] = await Promise.all([
        api.get('/mentorship/list').catch(() => ({ data: [] })),
        api.get('/mentorship/knowledge').catch(() => ({ data: [] })),
      ]);
      setMentorships(m.data);
      setKnowledge(k.data);
    } catch {}
  };

  const uploadFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      await api.post('/mentorship/upload-knowledge', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      loadData();
    } catch (err) { console.error(err); }
    e.target.value = '';
  };

  const deleteKnowledge = async (id) => {
    await api.delete(`/mentorship/knowledge/${id}`);
    loadData();
  };

  const generateMentorship = async () => {
    if (!form.knowledge_text && knowledge.length === 0) return;
    setGenerating(true);
    try {
      // axios timeout 6 min pra acomodar geração longa no Ollama
      const { data } = await api.post('/mentorship/generate', form, { timeout: 6 * 60 * 1000 });
      setMentorships(prev => [data, ...prev]);
      setViewing(data);
      setTab('list');
      setForm({ title: '', knowledge_text: '', niche: '', target_audience: '', duration_weeks: 8 });
      toast.success('Mentoria gerada com sucesso');
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Erro desconhecido';
      toast.error(`Erro ao gerar: ${msg}`);
      console.error('Mentorship generation failed:', e);
    }
    setGenerating(false);
  };

  const deleteMentorship = async (id) => {
    await api.delete(`/mentorship/${id}`);
    if (viewing?.id === id) setViewing(null);
    loadData();
  };

  const tabs = [
    { id: 'create', label: 'Criar Mentoria' },
    { id: 'list', label: `Mentorias (${mentorships.length})` },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div data-testid="mentorship-panel" className="w-full max-w-3xl animate-fade-in max-h-[90vh] flex flex-col"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        {/* Header */}
        <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="p-1.5" style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <h2 className="text-lg font-bold" style={{ fontFamily: 'Outfit' }}>Criador de Mentorias</h2>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Transforme seu conhecimento em uma mentoria completa</p>
            </div>
          </div>
          <button onClick={onClose} style={{ color: 'var(--text-tertiary)' }}><X className="w-5 h-5" /></button>
        </div>

        {/* Tabs */}
        <div className="flex" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => { setTab(t.id); setViewing(null); }}
              className="flex-1 py-3 text-xs font-medium transition-colors"
              style={{ color: tab === t.id ? 'var(--accent)' : 'var(--text-tertiary)', borderBottom: tab === t.id ? '2px solid var(--accent)' : '2px solid transparent' }}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {/* VIEWING/EDITING a mentorship */}
          {viewing && (
            <MentorshipEditor
              mentorship={viewing}
              onBack={() => setViewing(null)}
              onUpdated={loadData}
            />
          )}

          {/* CREATE tab */}
          {tab === 'create' && !viewing && (
            <div className="flex flex-col gap-4">
              {/* Knowledge base */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                    Base de Conhecimento ({knowledge.length} arquivos)
                  </p>
                  <div>
                    <input ref={fileRef} type="file" className="hidden" accept=".txt,.md,.csv,.json" onChange={uploadFile} />
                    <button onClick={() => fileRef.current?.click()}
                      className="px-3 py-1.5 text-xs font-medium flex items-center gap-1.5"
                      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                      <Upload className="w-3 h-3" /> Upload
                    </button>
                  </div>
                </div>
                {knowledge.length > 0 && (
                  <div className="flex flex-col gap-1 mb-2">
                    {knowledge.map(k => (
                      <div key={k.id} className="flex items-center gap-2 p-2"
                        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                        <FileText className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
                        <span className="text-xs flex-1 truncate">{k.filename}</span>
                        <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>{(k.size / 1024).toFixed(1)}KB</span>
                        <button onClick={() => deleteKnowledge(k.id)} className="p-1" style={{ color: 'var(--text-tertiary)' }}>
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Knowledge text */}
              <div>
                <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--text-secondary)' }}>
                  Seu Conhecimento (descreva tudo que sabe sobre o tema)
                </label>
                <textarea
                  data-testid="knowledge-text-input"
                  value={form.knowledge_text}
                  onChange={e => setForm({ ...form, knowledge_text: e.target.value })}
                  rows={8}
                  className="w-full py-3 px-4 text-sm outline-none resize-none"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
                  placeholder="Cole aqui todo o seu conhecimento sobre o tema da mentoria. Quanto mais detalhado, melhor sera o resultado. Voce pode descrever: sua experiencia, metodologias, frameworks, cases de sucesso, ferramentas que usa, resultados que ja alcancou, erros comuns no mercado..."
                />
              </div>

              {/* Details */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>Nicho</label>
                  <input value={form.niche} onChange={e => setForm({ ...form, niche: e.target.value })}
                    placeholder="Ex: Marketing Digital" className="w-full py-2 px-3 text-sm outline-none"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                </div>
                <div>
                  <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>Publico-alvo</label>
                  <input value={form.target_audience} onChange={e => setForm({ ...form, target_audience: e.target.value })}
                    placeholder="Ex: Iniciantes em negocio online" className="w-full py-2 px-3 text-sm outline-none"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                </div>
                <div>
                  <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>Nome da Mentoria (opcional)</label>
                  <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
                    placeholder="Sera gerado automaticamente" className="w-full py-2 px-3 text-sm outline-none"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                </div>
                <div>
                  <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>Duracao (semanas)</label>
                  <input type="number" value={form.duration_weeks} onChange={e => setForm({ ...form, duration_weeks: parseInt(e.target.value) || 8 })}
                    className="w-full py-2 px-3 text-sm outline-none"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                </div>
              </div>

              {/* Generate button */}
              <button
                data-testid="generate-mentorship-btn"
                onClick={generateMentorship}
                disabled={generating || (!form.knowledge_text && knowledge.length === 0)}
                className="w-full py-3 text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
                style={{
                  background: generating ? 'var(--bg-elevated)' : 'var(--accent)',
                  color: generating ? 'var(--text-secondary)' : 'var(--accent-text)',
                  opacity: (!form.knowledge_text && knowledge.length === 0) ? 0.5 : 1,
                }}>
                {generating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Gerando mentoria completa... (pode levar 2-5 minutos dependendo do modelo)
                  </>
                ) : (
                  <>
                    <GraduationCap className="w-4 h-4" />
                    Gerar Mentoria Completa com IA
                  </>
                )}
              </button>

              <div className="p-3" style={{ background: 'var(--terminal-bg)', border: '1px solid var(--border-subtle)' }}>
                <p className="text-xs font-mono" style={{ color: 'var(--terminal-text)' }}>
                  A IA vai criar: nome, promessa, modulos detalhados (min 6), aulas (min 4 por modulo), exercicios, bonus, metodologia, resultados, FAQ, copy de vendas e precificacao.
                </p>
              </div>
            </div>
          )}

          {/* LIST tab */}
          {tab === 'list' && !viewing && (
            <div className="flex flex-col gap-3">
              {mentorships.length === 0 && (
                <div className="text-center py-8">
                  <BookOpen className="w-8 h-8 mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
                  <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Nenhuma mentoria criada.</p>
                  <button onClick={() => setTab('create')} className="mt-2 text-xs" style={{ color: 'var(--accent)' }}>Criar primeira mentoria</button>
                </div>
              )}
              {mentorships.map(m => (
                <div key={m.id} className="p-4 cursor-pointer group transition-colors"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}
                  onClick={() => setViewing(m)}>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 flex items-center justify-center" style={{ background: 'var(--accent)' }}>
                        <GraduationCap className="w-5 h-5" style={{ color: 'var(--accent-text)' }} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold">{m.title}</p>
                        <div className="flex gap-2 text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
                          {m.niche && <span>{m.niche}</span>}
                          {m.duration_weeks && <span>{m.duration_weeks} semanas</span>}
                          <span>{new Date(m.created_at).toLocaleDateString('pt-BR')}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-xs px-1.5 py-0.5" style={{
                        background: m.status === 'published' ? 'rgba(34,197,94,0.15)' : 'rgba(255,214,0,0.15)',
                        color: m.status === 'published' ? 'var(--success)' : 'var(--accent)',
                      }}>{m.status === 'published' ? 'Publicada' : 'Rascunho'}</span>
                      <button onClick={(e) => { e.stopPropagation(); deleteMentorship(m.id); }}
                        className="p-1 opacity-0 group-hover:opacity-100" style={{ color: 'var(--text-tertiary)' }}>
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <p className="text-xs mt-2 line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                    {(m.content || '').slice(0, 200)}...
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
