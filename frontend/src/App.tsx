import React, { useState, useEffect } from 'react';
import { Send, CheckCircle, XCircle, Clock, AlertTriangle, Loader2, X } from 'lucide-react';

interface Task {
  task_id: string;
  description: string;
  status: string;
  result?: string;
  error?: string;
  pending_action?: { action: string; target: string };
  history?: Array<{ pending_action?: { action: string; target: string }; request_id?: string }>;
}

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiKey, setApiKey] = useState("");

  const fetchTasks = async () => {
      // In a real app we'd have a GET /tasks endpoint.
      // Since MVP API only has GET /tasks/{task_id}, we'll poll existing tasks
      const resList = await fetch('/api/tasks', { headers: { 'Authorization': apiKey }});
      if (resList.ok) {
          const listData = await resList.json();
          // We map over them and add any client-side history state if we were fetching it individually, but for MVP just showing the list is fine
          setTasks(listData);
          return;
      }

      const updatedTasks = await Promise.all(
          tasks.map(async (t) => {
              if (t.status === 'succeeded' || t.status === 'failed' || t.status === 'cancelled') return t;
              try {
                  const res = await fetch(`/api/tasks/${t.task_id}`, {
                      headers: { 'Authorization': apiKey }
                  });
                  if (res.ok) {
                      return await res.json();
                  }
              } catch (e) {
                  console.error(e);
              }
              return t;
          })
      );
      setTasks(updatedTasks);
  };

  useEffect(() => {
      const interval = setInterval(fetchTasks, 2000);
      return () => clearInterval(interval);
  }, [tasks, apiKey]);

  const submitTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setLoading(true);
    try {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': apiKey },
        body: JSON.stringify({ description: input })
      });
      if (res.ok) {
        const data = await res.json();
        setTasks([data, ...tasks]);
        setInput("");
      } else {
        alert("Failed to submit task. Check API Key.");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const resolveApproval = async (taskId: string, action: string) => {
      // Find request_id from history (hack for MVP since GET /tasks doesn't cleanly expose request_id yet)
      const task = tasks.find(t => t.task_id === taskId);
      if (!task || !task.history) return;
      const approvalEntry = [...task.history].reverse().find(e => e.request_id);
      if (!approvalEntry || !approvalEntry.request_id) return;

      try {
          await fetch(`/api/approvals/${approvalEntry.request_id}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Authorization': apiKey },
              body: JSON.stringify({ action: action, user_id: 'dashboard_user' })
          });
          fetchTasks();
      } catch (e) {
          console.error(e);
      }
  };

  const cancelTask = async (taskId: string) => {
      try {
          await fetch(`/api/tasks/${taskId}/cancel`, {
              method: 'POST',
              headers: { 'Authorization': apiKey }
          });
          fetchTasks();
      } catch (e) {
          console.error(e);
      }
  }

  const getStatusIcon = (status: string) => {
    switch(status) {
      case 'succeeded': return <CheckCircle className="text-green-500" />;
      case 'failed': return <XCircle className="text-red-500" />;
      case 'waiting_for_approval': return <AlertTriangle className="text-yellow-500" />;
      case 'queued':
      case 'planning':
      case 'running':
      case 'verifying':
        return <Loader2 className="animate-spin text-blue-500" />;
      default: return <Clock className="text-gray-500" />;
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem' }}>
      <header style={{ borderBottom: '1px solid #ddd', paddingBottom: '1rem', marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0 }}>JARVIS OS</h1>
        <div>
            <input
              type="password"
              placeholder="API Key (if required)"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
            />
        </div>
      </header>

      <main>
        <form onSubmit={submitTask} style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask JARVIS to do something..."
            style={{ flex: 1, padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc', fontSize: '1rem' }}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()} style={{ padding: '0.75rem 1.5rem', background: '#0066cc', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {loading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
            Send
          </button>
        </form>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {tasks.map(task => (
            <div key={task.task_id} style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0 }}>{task.description}</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', fontWeight: 600, textTransform: 'uppercase' }}>
                  {getStatusIcon(task.status)}
                  {task.status.replace(/_/g, ' ')}
                  {!['succeeded', 'failed', 'cancelled'].includes(task.status) && (
                      <button onClick={() => cancelTask(task.task_id)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, marginLeft: '0.5rem', color: '#dc2626' }}>
                          <X size={16} />
                      </button>
                  )}
                </div>
              </div>

              {task.status === 'waiting_for_approval' && (
                  <div style={{ background: '#fef3c7', padding: '1rem', borderRadius: '4px', marginBottom: '1rem' }}>
                      <strong>Approval Required:</strong> An agent wishes to execute an action.
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                          <button onClick={() => resolveApproval(task.task_id, 'approve')} style={{ padding: '0.5rem 1rem', background: '#10b981', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Approve</button>
                          <button onClick={() => resolveApproval(task.task_id, 'reject')} style={{ padding: '0.5rem 1rem', background: '#ef4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Reject</button>
                      </div>
                  </div>
              )}

              {task.error && (
                <div style={{ background: '#fee2e2', color: '#991b1b', padding: '1rem', borderRadius: '4px', fontSize: '0.875rem' }}>
                  <strong>Error:</strong> {task.error}
                </div>
              )}

              {task.result && (
                <div style={{ background: '#f3f4f6', color: '#374151', padding: '1rem', borderRadius: '4px', fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                  {task.result}
                </div>
              )}
            </div>
          ))}
          {tasks.length === 0 && <p style={{ textAlign: 'center', color: '#666' }}>No tasks executed yet.</p>}
        </div>
      </main>
    </div>
  );
}
