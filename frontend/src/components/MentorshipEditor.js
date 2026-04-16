import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  ArrowLeft, Plus, Trash2, GripVertical, ChevronDown, ChevronUp,
  Save, Loader2, BookOpen, FileText, Clock, Pencil, Check, X
} from 'lucide-react';

function LessonItem({ lesson, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [data, setData] = useState(lesson);

  const save = () => { onUpdate(data); setEditing(false); };

  if (editing) {
    return (
      <div className="p-3 flex flex-col gap-2 animate-fade-in" style={{ background: 'var(--bg-base)', border: '1px solid var(--accent)' }}>
        <input value={data.title} onChange={e => setData({ ...data, title: e.target.value })}
          className="w-full py-1.5 px-2 text-sm outline-none" placeholder="Titulo da aula"
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
        <textarea value={data.content || ''} onChange={e => setData({ ...data, content: e.target.value })}
          rows={3} className="w-full py-1.5 px-2 text-sm outline-none resize-none" placeholder="Conteudo/descricao da aula..."
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
        <div className="flex gap-2">
          <input value={data.duration || ''} onChange={e => setData({ ...data, duration: e.target.value })}
            className="flex-1 py-1.5 px-2 text-sm outline-none" placeholder="Duracao (ex: 45min)"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
          <button onClick={save} className="p-1.5" style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
            <Check className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => setEditing(false)} className="p-1.5" style={{ color: 'var(--text-tertiary)', border: '1px solid var(--border-subtle)' }}>
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 p-2 group" style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)' }}>
      <BookOpen className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--text-tertiary)' }} />
      <span className="flex-1 text-xs truncate">{lesson.title}</span>
      {lesson.duration && <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>{lesson.duration}</span>}
      <button onClick={() => setEditing(true)} className="p-1 opacity-0 group-hover:opacity-100" style={{ color: 'var(--text-tertiary)' }}>
        <Pencil className="w-3 h-3" />
      </button>
      <button onClick={() => onDelete(lesson.id)} className="p-1 opacity-0 group-hover:opacity-100" style={{ color: 'var(--text-tertiary)' }}>
        <Trash2 className="w-3 h-3" />
      </button>
    </div>
  );
}

function ModuleCard({ module, onUpdate, onDelete, onAddLesson, onUpdateLesson, onDeleteLesson }) {
  const [open, setOpen] = useState(false);
  const [editTitle, setEditTitle] = useState(false);
  const [title, setTitle] = useState(module.title);
  const [objective, setObjective] = useState(module.objective || '');

  const saveTitle = () => {
    onUpdate({ ...module, title, objective });
    setEditTitle(false);
  };

  return (
    <div className="animate-fade-in" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
      {/* Module header */}
      <div className="flex items-center gap-2 p-3 cursor-pointer" onClick={() => setOpen(!open)}>
        <div className="w-7 h-7 flex-shrink-0 flex items-center justify-center text-xs font-bold"
          style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
          {module.order + 1}
        </div>
        <div className="flex-1 min-w-0">
          {editTitle ? (
            <div className="flex gap-1" onClick={e => e.stopPropagation()}>
              <input value={title} onChange={e => setTitle(e.target.value)} autoFocus
                className="flex-1 py-0.5 px-1 text-sm outline-none"
                style={{ background: 'var(--bg-base)', border: '1px solid var(--accent)', color: 'var(--text-primary)' }} />
              <button onClick={saveTitle} className="p-0.5" style={{ color: 'var(--success)' }}><Check className="w-3.5 h-3.5" /></button>
            </div>
          ) : (
            <p className="text-sm font-medium truncate">{module.title}</p>
          )}
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            {(module.lessons || []).length} aulas
            {module.objective && ` · ${module.objective.slice(0, 40)}`}
          </p>
        </div>
        <button onClick={e => { e.stopPropagation(); setEditTitle(!editTitle); }} className="p-1" style={{ color: 'var(--text-tertiary)' }}>
          <Pencil className="w-3 h-3" />
        </button>
        <button onClick={e => { e.stopPropagation(); onDelete(module.id); }} className="p-1" style={{ color: 'var(--text-tertiary)' }}>
          <Trash2 className="w-3 h-3" />
        </button>
        {open ? <ChevronUp className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} /> : <ChevronDown className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />}
      </div>

      {/* Module body */}
      {open && (
        <div className="px-3 pb-3 flex flex-col gap-1.5" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          {editTitle && (
            <input value={objective} onChange={e => setObjective(e.target.value)} onClick={e => e.stopPropagation()}
              placeholder="Objetivo do modulo..." className="w-full py-1.5 px-2 text-xs outline-none mt-2"
              style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
          )}
          <div className="mt-2 flex flex-col gap-1">
            {(module.lessons || []).sort((a, b) => (a.order || 0) - (b.order || 0)).map(lesson => (
              <LessonItem key={lesson.id} lesson={lesson}
                onUpdate={(updated) => onUpdateLesson(module.id, updated)}
                onDelete={(lessonId) => onDeleteLesson(module.id, lessonId)} />
            ))}
          </div>
          <button onClick={() => onAddLesson(module.id)}
            className="w-full py-1.5 text-xs flex items-center justify-center gap-1 mt-1"
            style={{ border: '1px dashed var(--border-subtle)', color: 'var(--text-tertiary)' }}>
            <Plus className="w-3 h-3" /> Adicionar Aula
          </button>
        </div>
      )}
    </div>
  );
}

export default function MentorshipEditor({ mentorship, onBack, onUpdated }) {
  const { api } = useAuth();
  const [modules, setModules] = useState([]);
  const [saving, setSaving] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (mentorship?.modules?.length > 0) {
      setModules(mentorship.modules);
    }
  }, [mentorship]);

  const parseFromContent = async () => {
    setParsing(true);
    try {
      const { data } = await api.post(`/mentorship/${mentorship.id}/parse-modules`);
      setModules(data);
    } catch (e) { console.error(e); }
    setParsing(false);
  };

  const saveAll = async () => {
    setSaving(true);
    try {
      const { data } = await api.put(`/mentorship/${mentorship.id}/modules`, modules);
      setModules(data);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      if (onUpdated) onUpdated();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const addModule = () => {
    setModules(prev => [...prev, {
      id: crypto.randomUUID(), title: `Modulo ${prev.length + 1}`,
      objective: '', order: prev.length, lessons: [], exercises: [], materials: []
    }]);
  };

  const deleteModule = (modId) => {
    setModules(prev => prev.filter(m => m.id !== modId).map((m, i) => ({ ...m, order: i })));
  };

  const updateModule = (updated) => {
    setModules(prev => prev.map(m => m.id === updated.id ? { ...m, ...updated } : m));
  };

  const addLesson = (modId) => {
    setModules(prev => prev.map(m => {
      if (m.id !== modId) return m;
      const lessons = [...(m.lessons || []), {
        id: crypto.randomUUID(), title: `Aula ${(m.lessons || []).length + 1}`,
        content: '', duration: '30min', order: (m.lessons || []).length
      }];
      return { ...m, lessons };
    }));
  };

  const updateLesson = (modId, updated) => {
    setModules(prev => prev.map(m => {
      if (m.id !== modId) return m;
      return { ...m, lessons: (m.lessons || []).map(l => l.id === updated.id ? updated : l) };
    }));
  };

  const deleteLesson = (modId, lessonId) => {
    setModules(prev => prev.map(m => {
      if (m.id !== modId) return m;
      return { ...m, lessons: (m.lessons || []).filter(l => l.id !== lessonId).map((l, i) => ({ ...l, order: i })) };
    }));
  };

  const exportFile = async (format) => {
    try {
      const response = await api.get(`/mentorship/${mentorship.id}/export/${format}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `${mentorship.title}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) { console.error(e); alert('Erro ao exportar'); }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-1 text-xs" style={{ color: 'var(--accent)' }}>
          <ArrowLeft className="w-3 h-3" /> Voltar
        </button>
        <div className="flex gap-2">
          <button onClick={() => exportFile('pdf')} className="px-3 py-1.5 text-xs flex items-center gap-1"
            style={{ border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
            <FileText className="w-3 h-3" /> PDF
          </button>
          <button onClick={() => exportFile('docx')} className="px-3 py-1.5 text-xs flex items-center gap-1"
            style={{ border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
            <FileText className="w-3 h-3" /> DOCX
          </button>
        </div>
      </div>

      <h3 className="text-lg font-bold" style={{ fontFamily: 'Outfit' }}>{mentorship.title}</h3>

      {/* Parse or build */}
      {modules.length === 0 && (
        <div className="flex gap-2">
          <button onClick={parseFromContent} disabled={parsing}
            className="flex-1 py-2.5 text-sm font-medium flex items-center justify-center gap-2"
            style={{ background: 'var(--accent)', color: 'var(--accent-text)' }}>
            {parsing ? <Loader2 className="w-4 h-4 animate-spin" /> : <BookOpen className="w-4 h-4" />}
            {parsing ? 'Extraindo modulos...' : 'Extrair Modulos do Conteudo'}
          </button>
          <button onClick={addModule} className="px-4 py-2.5 text-sm flex items-center gap-2"
            style={{ border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
            <Plus className="w-4 h-4" /> Manual
          </button>
        </div>
      )}

      {/* Modules list */}
      {modules.length > 0 && (
        <>
          <div className="flex flex-col gap-2">
            {modules.sort((a, b) => a.order - b.order).map(mod => (
              <ModuleCard key={mod.id} module={mod}
                onUpdate={updateModule} onDelete={deleteModule}
                onAddLesson={addLesson} onUpdateLesson={updateLesson} onDeleteLesson={deleteLesson} />
            ))}
          </div>

          <button onClick={addModule}
            className="w-full py-2 text-xs flex items-center justify-center gap-1"
            style={{ border: '1px dashed var(--border-subtle)', color: 'var(--text-tertiary)' }}>
            <Plus className="w-3.5 h-3.5" /> Adicionar Modulo
          </button>

          <button onClick={saveAll} disabled={saving}
            className="w-full py-3 text-sm font-semibold flex items-center justify-center gap-2"
            style={{ background: saved ? 'var(--success)' : 'var(--accent)', color: saved ? 'white' : 'var(--accent-text)' }}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saved ? 'Salvo!' : saving ? 'Salvando...' : 'Salvar Modulos'}
          </button>
        </>
      )}
    </div>
  );
}
