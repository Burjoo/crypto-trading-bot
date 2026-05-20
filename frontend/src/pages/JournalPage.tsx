import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Plus, Tag, Star, Smile, BarChart3, X } from 'lucide-react';
import { clsx } from 'clsx';
import { format } from 'date-fns';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../store';
import toast from 'react-hot-toast';

const EMOTIONS = ['confident', 'neutral', 'fearful', 'greedy', 'fomo', 'patient'];
const EMOTION_COLORS: Record<string, string> = {
  confident: '#00ff87', neutral: '#8899aa', fearful: '#ff3b6b',
  greedy: '#ffd900', fomo: '#ff7c2a', patient: '#00d4ff',
};

export default function JournalPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [activeTab, setActiveTab] = useState<'entries' | 'analytics'>('entries');
  const [form, setForm] = useState({
    title: '', notes: '', emotion: '', mistakes: '',
    lessons: '', setup_quality: 5, tags: [] as string[],
  });
  const [tagInput, setTagInput] = useState('');

  const { data: entriesData, isLoading } = useQuery({
    queryKey: ['journal'],
    queryFn: () => api.get('/journal?limit=50').then(r => r.data),
  });
  const { data: analytics } = useQuery({
    queryKey: ['journal-analytics'],
    queryFn: () => api.get('/journal/analytics').then(r => r.data),
  });

  const createEntry = useMutation({
    mutationFn: () => api.post('/journal', form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['journal'] });
      qc.invalidateQueries({ queryKey: ['journal-analytics'] });
      setShowForm(false);
      setForm({ title:'', notes:'', emotion:'', mistakes:'', lessons:'', setup_quality:5, tags:[] });
      toast.success('Journal entry saved');
    },
    onError: () => toast.error('Failed to save entry'),
  });

  const addTag = () => {
    const t = tagInput.trim().toLowerCase();
    if (t && !form.tags.includes(t)) {
      setForm(p => ({ ...p, tags: [...p.tags, t] }));
    }
    setTagInput('');
  };

  const entries = entriesData?.entries ?? [];
  const emotionData = Object.entries(analytics?.emotion_distribution ?? {}).map(([name, value]) => ({
    name, value: value as number, color: EMOTION_COLORS[name] ?? '#8899aa',
  }));

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-2xl text-text-primary flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-accent-cyan" /> Trading Journal
          </h1>
          <p className="text-text-secondary text-sm mt-0.5">{analytics?.total_entries ?? 0} entries</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2 text-sm">
          <Plus className="w-4 h-4" /> New Entry
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-bg-border">
        {(['entries', 'analytics'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={clsx('px-5 py-2.5 text-sm font-medium capitalize transition-colors',
              activeTab === tab
                ? 'text-accent-cyan border-b-2 border-accent-cyan'
                : 'text-text-muted hover:text-text-secondary'
            )}>
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'entries' && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {isLoading ? (
            Array.from({length:6}).map((_,i) => (
              <div key={i} className="card p-5 space-y-3 animate-pulse">
                <div className="h-5 bg-bg-elevated rounded w-3/4" />
                <div className="h-4 bg-bg-elevated rounded w-1/2" />
                <div className="h-3 bg-bg-elevated rounded w-full" />
              </div>
            ))
          ) : entries.length === 0 ? (
            <div className="col-span-full card p-12 flex flex-col items-center justify-center text-text-muted gap-3">
              <BookOpen className="w-12 h-12 opacity-20" />
              <p className="font-medium text-text-secondary">No journal entries yet</p>
              <p className="text-sm">Start documenting your trades and lessons learned</p>
              <button onClick={() => setShowForm(true)} className="btn-primary text-sm mt-2 flex items-center gap-2">
                <Plus className="w-4 h-4" /> First Entry
              </button>
            </div>
          ) : (
            entries.map((e: any) => (
              <div key={e.id} className="card p-5 flex flex-col gap-3 hover:border-bg-border/80 transition-all cursor-pointer">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-medium text-text-primary line-clamp-2">{e.title}</h3>
                  {e.emotion && (
                    <span className="text-xs px-2 py-0.5 rounded-full flex-shrink-0"
                      style={{ background: `${EMOTION_COLORS[e.emotion]}15`, color: EMOTION_COLORS[e.emotion], border: `1px solid ${EMOTION_COLORS[e.emotion]}30` }}>
                      {e.emotion}
                    </span>
                  )}
                </div>
                {e.setup_quality && (
                  <div className="flex items-center gap-1">
                    {Array.from({length:10}).map((_,i) => (
                      <div key={i} className={clsx('h-1.5 flex-1 rounded-full', i < e.setup_quality ? 'bg-accent-cyan' : 'bg-bg-elevated')} />
                    ))}
                    <span className="text-xs text-text-muted ml-1">{e.setup_quality}/10</span>
                  </div>
                )}
                {e.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {e.tags.slice(0,4).map((tag: string) => (
                      <span key={tag} className="text-2xs px-1.5 py-0.5 rounded bg-bg-elevated text-text-muted border border-bg-border">
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-xs text-text-muted mt-auto">
                  {e.created_at ? format(new Date(e.created_at), 'MMM d, yyyy') : ''}
                </p>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'analytics' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card p-5">
            <h2 className="section-title mb-4">Emotion Distribution</h2>
            {emotionData.length > 0 ? (
              <div className="flex items-center gap-6">
                <ResponsiveContainer width={160} height={160}>
                  <PieChart>
                    <Pie data={emotionData} dataKey="value" cx="50%" cy="50%" outerRadius={70} innerRadius={40}>
                      {emotionData.map((d, i) => <Cell key={i} fill={d.color} />)}
                    </Pie>
                    <Tooltip formatter={(v: any, n: any) => [v, n]} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2">
                  {emotionData.map(d => (
                    <div key={d.name} className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: d.color }} />
                      <span className="text-sm text-text-secondary capitalize">{d.name}</span>
                      <span className="text-sm font-mono text-text-muted ml-auto">{d.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-32 flex items-center justify-center text-text-muted text-sm">
                No emotion data yet
              </div>
            )}
          </div>

          <div className="card p-5">
            <h2 className="section-title mb-4">Stats</h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center py-2 border-b border-bg-border">
                <span className="text-text-secondary text-sm">Total Entries</span>
                <span className="font-mono font-medium text-text-primary">{analytics?.total_entries ?? 0}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-bg-border">
                <span className="text-text-secondary text-sm">Avg Setup Quality</span>
                <span className="font-mono font-medium text-accent-cyan">{analytics?.avg_setup_quality ?? 0}/10</span>
              </div>
              <div className="pt-1">
                <p className="text-text-secondary text-sm mb-2">Top Tags</p>
                <div className="flex flex-wrap gap-1.5">
                  {(analytics?.top_tags ?? []).slice(0,8).map(([tag, count]: [string, number]) => (
                    <span key={tag} className="text-xs px-2 py-0.5 rounded-full bg-bg-elevated border border-bg-border text-text-secondary">
                      #{tag} <span className="text-accent-cyan">{count}</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-start justify-center p-4 overflow-y-auto">
          <div className="card w-full max-w-xl p-6 my-8 animate-slide-in">
            <div className="flex items-center justify-between mb-5">
              <h2 className="section-title">New Journal Entry</h2>
              <button onClick={() => setShowForm(false)} className="text-text-muted hover:text-text-primary">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="label">Title *</label>
                <input value={form.title} onChange={e => setForm(p=>({...p,title:e.target.value}))}
                  className="input" placeholder="E.g. BTC breakout trade review" />
              </div>
              <div>
                <label className="label">Emotion</label>
                <div className="flex flex-wrap gap-2">
                  {EMOTIONS.map(em => (
                    <button key={em} onClick={() => setForm(p=>({...p, emotion: p.emotion === em ? '' : em}))}
                      className={clsx('px-3 py-1 rounded-full text-xs capitalize transition-all',
                        form.emotion === em
                          ? 'text-bg-primary font-semibold'
                          : 'bg-bg-elevated text-text-muted border border-bg-border hover:border-bg-border/80'
                      )}
                      style={form.emotion === em ? { background: EMOTION_COLORS[em] } : {}}>
                      {em}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="label">Setup Quality: {form.setup_quality}/10</label>
                <input type="range" min={1} max={10} value={form.setup_quality}
                  onChange={e => setForm(p=>({...p, setup_quality: +e.target.value}))}
                  className="w-full accent-accent-cyan" />
              </div>
              <div>
                <label className="label">Notes</label>
                <textarea value={form.notes} onChange={e => setForm(p=>({...p,notes:e.target.value}))}
                  className="input h-24 resize-none" placeholder="What happened? Why did you take this trade?" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Mistakes</label>
                  <textarea value={form.mistakes} onChange={e => setForm(p=>({...p,mistakes:e.target.value}))}
                    className="input h-20 resize-none" placeholder="What went wrong?" />
                </div>
                <div>
                  <label className="label">Lessons</label>
                  <textarea value={form.lessons} onChange={e => setForm(p=>({...p,lessons:e.target.value}))}
                    className="input h-20 resize-none" placeholder="What did you learn?" />
                </div>
              </div>
              <div>
                <label className="label">Tags</label>
                <div className="flex gap-2">
                  <input value={tagInput} onChange={e => setTagInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addTag())}
                    className="input text-sm" placeholder="Add tag, press Enter" />
                  <button onClick={addTag} className="btn-secondary px-3"><Tag className="w-4 h-4" /></button>
                </div>
                {form.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {form.tags.map(tag => (
                      <span key={tag} className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-bg-elevated border border-bg-border text-text-secondary">
                        #{tag}
                        <button onClick={() => setForm(p=>({...p, tags: p.tags.filter(t=>t!==tag)}))}
                          className="text-text-muted hover:text-accent-red ml-0.5"><X className="w-3 h-3" /></button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowForm(false)} className="btn-secondary flex-1">Cancel</button>
              <button onClick={() => createEntry.mutate()}
                disabled={createEntry.isPending || !form.title}
                className="btn-primary flex-1 flex items-center justify-center gap-2">
                {createEntry.isPending
                  ? <span className="w-4 h-4 border-2 border-bg-primary/30 border-t-bg-primary rounded-full animate-spin" />
                  : <BookOpen className="w-4 h-4" />}
                Save Entry
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
