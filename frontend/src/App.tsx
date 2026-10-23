import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  Activity, AlertCircle, ArrowDownLeft, ArrowUpRight, Bot, Check, CheckCircle2,
  ChevronDown, Circle, Code2, Command, FileText, History, LoaderCircle,
  Menu, Plus, RefreshCw, Search, Send, ShieldCheck, Sparkles, TerminalSquare, X,
  XCircle, XOctagon, Zap
} from 'lucide-react';
import './styles.css';

type TaskStatus = 'queued' | 'planning' | 'running' | 'verifying' | 'waiting_for_approval' | 'succeeded' | 'failed' | 'cancelled' | string;
interface Task {
  task_id: string;
  description: string;
  status: TaskStatus;
  result?: string | null;
  error?: string | null;
  history?: Array<{ request_id?: string; pending_action?: { action?: string; target?: string }; [key: string]: unknown }>;
  assigned_agent_id?: string | null;
  created_at?: string;
}
type View = 'workspace' | 'activity' | 'artifacts';

const terminal = (s: string) => ['succeeded', 'failed', 'cancelled'].includes(s);
const pretty = (s: string) => (s || 'unknown').replace(/_/g, ' ');
const agentNames = ['Research', 'Developer', 'Operations', 'Communications', 'QA / Security'];

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [prompt, setPrompt] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [keyVisible, setKeyVisible] = useState(false);
  const [search, setSearch] = useState('');
  const [view, setView] = useState<View>('workspace');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [mobileSidebar, setMobileSidebar] = useState(false);
  const [approvalBusy, setApprovalBusy] = useState(false);

  const request = useCallback(async (path: string, init: RequestInit = {}) => {
    const headers = new Headers(init.headers);
    if (apiKey.trim()) headers.set('Authorization', apiKey.trim());
    if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    const response = await fetch(`/api${path}`, { ...init, headers });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`API ${response.status}: ${body.slice(0, 220) || response.statusText}`);
    }
    if (response.status === 204) return null;
    return response.json();
  }, [apiKey]);

  const refreshTasks = useCallback(async (quiet = false) => {
    if (!quiet) setRefreshing(true);
    try {
      const data = await request('/tasks');
      if (!Array.isArray(data)) throw new Error('The tasks endpoint returned an unexpected response.');
      const ordered = [...data].sort((a: Task, b: Task) => {
        const da = a.created_at ? new Date(a.created_at).getTime() : 0;
        const db = b.created_at ? new Date(b.created_at).getTime() : 0;
        return db - da;
      });
      setTasks(ordered);
      setSelectedId(current => current && ordered.some((t: Task) => t.task_id === current) ? current : ordered[0]?.task_id || '');
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load tasks.');
    } finally {
      if (!quiet) setRefreshing(false);
    }
  }, [request]);

  useEffect(() => { void refreshTasks(); }, [refreshTasks]);
  useEffect(() => {
    const id = window.setInterval(() => { void refreshTasks(true); }, 3000);
    return () => window.clearInterval(id);
  }, [refreshTasks]);

  const selected = tasks.find(task => task.task_id === selectedId) || null;
  const filtered = useMemo(() => tasks.filter(t => t.description.toLowerCase().includes(search.toLowerCase())), [tasks, search]);
  const activeCount = tasks.filter(t => !terminal(t.status)).length;
  const succeededCount = tasks.filter(t => t.status === 'succeeded').length;
  const approvalEntry = selected?.history?.slice().reverse().find(entry => entry.request_id && entry.pending_action);
  const pendingAction = approvalEntry?.pending_action;

  const submitTask = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!prompt.trim() || loading) return;
    setLoading(true); setError(''); setNotice('');
    try {
      const task = await request('/tasks', { method: 'POST', body: JSON.stringify({ description: prompt.trim() }) }) as Task;
      setTasks(current => [task, ...current.filter(t => t.task_id !== task.task_id)]);
      setSelectedId(task.task_id); setPrompt(''); setView('workspace');
      setNotice('Task submitted to the JARVIS backend.');
      void refreshTasks(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Task submission failed.');
    } finally { setLoading(false); }
  };

  const cancelTask = async () => {
    if (!selected) return;
    try {
      await request(`/tasks/${encodeURIComponent(selected.task_id)}/cancel`, { method: 'POST' });
      setNotice('Cancellation request sent.');
      await refreshTasks(true);
    } catch (e) { setError(e instanceof Error ? e.message : 'Cancellation failed.'); }
  };

  const resolveApproval = async (action: 'approve' | 'reject') => {
    if (!approvalEntry?.request_id) {
      setError('The API response does not expose a pending approval request ID for this task.');
      return;
    }
    setApprovalBusy(true); setError('');
    try {
      await request(`/approvals/${encodeURIComponent(approvalEntry.request_id)}`, {
        method: 'POST', body: JSON.stringify({ action, user_id: 'dashboard_user' })
      });
      setNotice(action === 'approve' ? 'Approval submitted.' : 'Rejection submitted.');
      await refreshTasks(true);
    } catch (e) { setError(e instanceof Error ? e.message : 'Approval action failed.'); }
    finally { setApprovalBusy(false); }
  };

  const statusIcon = (status: string) => {
    if (status === 'succeeded') return <CheckCircle2 size={15} />;
    if (status === 'failed') return <XCircle size={15} />;
    if (status === 'cancelled') return <XOctagon size={15} />;
    if (status === 'waiting_for_approval') return <ShieldCheck size={15} />;
    if (!terminal(status)) return <LoaderCircle size={15} className="spin" />;
    return <Circle size={15} />;
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileSidebar ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><Sparkles size={21} /></div>
          <div><div className="brand-name">JARVIS<span>OS</span></div><div className="brand-caption">PERSONAL AGENT SYSTEM</div></div>
          <button className="icon-button sidebar-close" aria-label="Close navigation" onClick={() => setMobileSidebar(false)}><X size={17} /></button>
        </div>
        <button className="new-task" onClick={() => { setPrompt(''); setView('workspace'); setSelectedId(''); setMobileSidebar(false); }}>
          <Plus size={17} /> New task <span>⌘ K</span>
        </button>
        <div className="side-label">WORKSPACE</div>
        <button className={`nav-item ${view === 'workspace' ? 'nav-active' : ''}`} onClick={() => setView('workspace')}><Command size={17} /> Command center</button>
        <button className={`nav-item ${view === 'activity' ? 'nav-active' : ''}`} onClick={() => setView('activity')}><Activity size={17} /> Activity & timeline</button>
        <button className={`nav-item ${view === 'artifacts' ? 'nav-active' : ''}`} onClick={() => setView('artifacts')}><Code2 size={17} /> Results & artifacts</button>
        <div className="side-label side-label-row"><span>RECENT TASKS</span><span className="tiny-count">{tasks.length}</span></div>
        <div className="task-search"><Search size={14} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search task history" aria-label="Search task history" /></div>
        <div className="history-list">
          {filtered.map(task => <button key={task.task_id} className={`history-item ${task.task_id === selectedId ? 'history-active' : ''}`} onClick={() => { setSelectedId(task.task_id); setMobileSidebar(false); }}>
            <span className={`history-status status-${task.status}`}>{statusIcon(task.status)}</span>
            <span className="history-copy"><span>{task.description}</span><small>{pretty(task.status)}</small></span>
          </button>)}
          {filtered.length === 0 && <div className="empty-history">{tasks.length ? 'No tasks match your search.' : 'Your task history will appear here.'}</div>}
        </div>
        <div className="sidebar-bottom">
          <div className="connection-row"><span className="connection-dot" /><span>API connection</span><strong>Polling</strong></div>
          <div className="sidebar-footnote">Local workspace · API-backed tasks</div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileSidebar(true)}><Menu size={19} /></button>
          <div className="breadcrumb"><span>JARVIS OS</span><ArrowDownLeft size={13} /><strong>{view === 'workspace' ? 'Workspace' : view === 'activity' ? 'Activity' : 'Artifacts'}</strong></div>
          <div className="topbar-right">
            <span className="runtime-pill"><span className="connection-dot" /> API connected by polling</span>
            <div className="api-key-wrap"><input type={keyVisible ? 'text' : 'password'} value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="API key (optional)" aria-label="JARVIS API key" /><button className="icon-button" onClick={() => setKeyVisible(v => !v)} aria-label={keyVisible ? 'Hide API key' : 'Show API key'}>{keyVisible ? <X size={15}/> : <ChevronDown size={15}/>}</button></div>
          </div>
        </header>

        <div className="content-area">
          <div className="welcome-row">
            <div><div className="eyebrow"><Zap size={13} /> AGENT COMMAND CENTER</div><h1>{view === 'workspace' ? 'What should we work on?' : view === 'activity' ? 'Execution activity' : 'Results & artifacts'}</h1><p>Delegate a task to JARVIS and track what the backend actually reports.</p></div>
            <button className="secondary-button" onClick={() => void refreshTasks()} disabled={refreshing}><RefreshCw size={15} className={refreshing ? 'spin' : ''} /> Refresh</button>
          </div>

          <div className="metrics-row">
            <div className="metric-card"><span className="metric-icon"><Activity size={16}/></span><div><small>ACTIVE TASKS</small><strong>{activeCount.toString().padStart(2, '0')}</strong></div></div>
            <div className="metric-card"><span className="metric-icon green"><Check size={16}/></span><div><small>SUCCEEDED</small><strong>{succeededCount.toString().padStart(2, '0')}</strong></div></div>
            <div className="metric-card"><span className="metric-icon violet"><History size={16}/></span><div><small>RECORDED TASKS</small><strong>{tasks.length.toString().padStart(2, '0')}</strong></div></div>
            <div className="metric-card"><span className="metric-icon amber"><ShieldCheck size={16}/></span><div><small>APPROVALS</small><strong>{tasks.filter(t => t.status === 'waiting_for_approval').length.toString().padStart(2, '0')}</strong></div></div>
          </div>

          {error && <div className="banner banner-error"><AlertCircle size={17}/><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X size={15}/></button></div>}
          {notice && <div className="banner banner-notice"><CheckCircle2 size={16}/><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss notice"><X size={15}/></button></div>}

          {view === 'workspace' && <section className="composer-panel">
            <div className="composer-top"><div className="composer-avatar"><Bot size={20}/></div><div><strong>JARVIS supervisor</strong><span>Task intake · real backend endpoint</span></div><span className="mode-chip">API MODE</span></div>
            <form onSubmit={submitTask}>
              <textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Describe a task for JARVIS… Be specific about the outcome you need." rows={3} disabled={loading} />
              <div className="composer-bottom"><span><span className="keyboard-dot"/> Tasks are submitted to POST /tasks</span><button type="submit" className="primary-button" disabled={loading || !prompt.trim()}>{loading ? <LoaderCircle size={16} className="spin"/> : <Send size={16}/>} Run task <ArrowUpRight size={15}/></button></div>
            </form>
          </section>}

          {view === 'activity' && <section className="panel activity-panel">
            <div className="panel-heading"><div><h2>Task status timeline</h2><p>Derived from current task status returned by the API.</p></div><span className="subtle-chip">POLLING · 3S</span></div>
            {!selected ? <div className="empty-state">Select a task from recent history to inspect its status.</div> : <div className="timeline">
              <div className="timeline-entry"><span className="timeline-dot"><Check size={13}/></span><div><strong>Task submitted</strong><p>{selected.description}</p><small>Creation time is not exposed by the current task response.</small></div><span className="timeline-state">RECORDED</span></div>
              <div className="timeline-entry"><span className={`timeline-dot ${terminal(selected.status) ? 'timeline-done' : 'timeline-live'}`}>{statusIcon(selected.status)}</span><div><strong>Current status: {pretty(selected.status)}</strong><p>{selected.error || selected.result || 'The API does not currently expose per-step execution events to the dashboard.'}</p></div><span className="timeline-state">{terminal(selected.status) ? 'FINAL' : 'CURRENT'}</span></div>
              <div className="capability-note"><AlertCircle size={16}/><div><strong>Detailed agent trace unavailable</strong><p>The backend has no public task-events endpoint in the current API contract. This timeline does not invent agent steps or tool calls.</p></div></div>
            </div>}
          </section>}

          {view === 'artifacts' && <section className="panel artifacts-panel">
            <div className="panel-heading"><div><h2>Deliverables</h2><p>Output returned by the selected task.</p></div><span className="subtle-chip"><FileText size={12}/> API RESULT</span></div>
            {!selected ? <div className="empty-state">Select a task to view its output.</div> : <>
              <div className="artifact-title"><FileText size={18}/><div><strong>{selected.description}</strong><small>{selected.task_id}</small></div><span className={`status-badge status-${selected.status}`}>{pretty(selected.status)}</span></div>
              {selected.result ? <pre className="result-block">{selected.result}</pre> : selected.error ? <pre className="result-block result-error">{selected.error}</pre> : <div className="empty-state">No result has been returned yet.</div>}
              <div className="capability-note"><Code2 size={16}/><div><strong>Code diff preview not available</strong><p>The API does not currently expose generated file manifests or diffs. This panel shows the actual task result only.</p></div></div>
            </>}
          </section>}

          <section className="panel task-panel">
            <div className="panel-heading"><div><h2>Selected task</h2><p>Live snapshot from the task API</p></div>{selected && <span className={`status-badge status-${selected.status}`}>{statusIcon(selected.status)} {pretty(selected.status)}</span>}</div>
            {!selected ? <div className="empty-state"><div className="empty-orb"><Sparkles size={23}/></div><strong>No task selected</strong><p>Submit a task above or select one from your history.</p></div> : <>
              <div className="selected-task-title"><div className="selected-task-icon"><TerminalSquare size={18}/></div><div><h3>{selected.description}</h3><small>ID · {selected.task_id}</small></div></div>
              {selected.status === 'waiting_for_approval' && <div className="approval-card"><div className="approval-icon"><ShieldCheck size={20}/></div><div className="approval-copy"><strong>Human approval required</strong><p>{pendingAction ? `${pendingAction.action || 'Action'} · ${pendingAction.target || 'target not specified'}` : 'The API reports a pending approval state, but the request details are not present in the task response.'}</p>{!approvalEntry?.request_id && <small>Approval controls unavailable until the API returns a request ID.</small>}</div><div className="approval-actions"><button disabled={approvalBusy || !approvalEntry?.request_id} onClick={() => void resolveApproval('reject')} className="reject-button">Reject</button><button disabled={approvalBusy || !approvalEntry?.request_id} onClick={() => void resolveApproval('approve')} className="approve-button">{approvalBusy ? <LoaderCircle size={14} className="spin"/> : <Check size={14}/>} Approve</button></div></div>}
              {selected.error && <div className="task-error"><AlertCircle size={16}/><div><strong>Execution error</strong><p>{selected.error}</p></div></div>}
              <div className="task-actions"><button className="secondary-button" onClick={() => { setView('activity'); }}><Activity size={14}/> View timeline</button><button className="secondary-button" onClick={() => setView('artifacts')}><FileText size={14}/> View result</button>{!terminal(selected.status) && <button className="danger-button" onClick={() => void cancelTask()}><XOctagon size={14}/> Cancel task</button>}</div>
              {selected.result && <div className="result-preview"><div className="result-preview-heading"><span><CheckCircle2 size={15}/> RESULT</span><button onClick={() => setView('artifacts')}>Open artifacts <ArrowUpRight size={13}/></button></div><pre>{selected.result}</pre></div>}
            </>}
          </section>

          <section className="panel specialists-panel">
            <div className="panel-heading"><div><h2>Specialist agents</h2><p>Configured roles in the supervisor architecture</p></div><span className="subtle-chip">5 ROLES</span></div>
            <div className="specialist-grid">{agentNames.map((name, i) => <div className="specialist-card" key={name}><div className={`specialist-symbol specialist-${i}`}>{i === 0 ? <Search size={16}/> : i === 1 ? <Code2 size={16}/> : i === 2 ? <Zap size={16}/> : i === 3 ? <FileText size={16}/> : <ShieldCheck size={16}/>}</div><div><strong>{name}</strong><small>{['Research and synthesis','Code and development','Operations and deployment','Communication workflows','Quality and safety'][i]}</small></div><span className="configured-dot" title="Configured role; live per-agent status is not exposed"/></div>)}</div>
            <div className="capability-note"><AlertCircle size={16}/><div><strong>Live per-agent activity is not exposed</strong><p>These are the five roles configured in the backend source, not a claim that each role is currently running. The current API returns task-level status only.</p></div></div>
          </section>

          <footer className="main-footer"><span><span className="connection-dot"/> JARVIS API · local development</span><span>Live updates via polling <span className="footer-separator">/</span> No fabricated telemetry</span></footer>
        </div>
      </main>
    </div>
  );
}
