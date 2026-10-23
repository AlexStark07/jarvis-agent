import React, { useState, useEffect } from 'react';
import { Send, CheckCircle, XCircle, Clock, AlertTriangle, Loader2, X, Terminal, Workflow, FileCode, CheckSquare, MessageSquare, Briefcase, Zap, ShieldAlert, Cpu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { JarvisCore, CoreState } from './components/JarvisCore';
import { AgentGraph } from './components/AgentGraph';

interface Task {
  task_id: string;
  description: string;
  status: string;
  result?: string;
  error?: string;
  agent_id?: string;
  pending_action?: { action: string; target: string };
  history?: Array<{ pending_action?: { action: string; target: string }; request_id?: string; approved_action?: string }>;
}

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'activity' | 'results' | 'logs'>('overview');

  const fetchTasks = async () => {
      try {
          const resList = await fetch('/api/tasks', { headers: { 'Authorization': apiKey }});
          if (resList.ok) {
              const listData = await resList.json();
              setTasks(listData);
          }
      } catch (e) {
          console.error("Failed to fetch tasks", e);
      }
  };

  useEffect(() => {
      fetchTasks();
      const interval = setInterval(fetchTasks, 2000);
      return () => clearInterval(interval);
  }, [apiKey]);

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
        setSelectedTaskId(data.task_id);
        setInput("");
      } else {
        alert("Failed to submit task. Check API Key.");
      }
    } catch (e) {
        console.error(e);
    }
    setLoading(false);
  };

  const resolveApproval = async (task: Task, action: 'approve' | 'reject') => {
      if (!task.history || task.history.length === 0) return;
      const approvalEntry = task.history.slice().reverse().find(h => h.request_id);
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
  };

  const getStatusIcon = (status: string) => {
    switch(status) {
      case 'succeeded': return <CheckCircle className="text-jarvis-cyan" />;
      case 'failed': return <XCircle className="text-red-500" />;
      case 'cancelled': return <XCircle className="text-gray-400" />;
      case 'waiting_for_approval': return <AlertTriangle className="text-yellow-400 animate-pulse" />;
      case 'queued':
      case 'planning':
      case 'running':
      case 'verifying':
        return <Loader2 className="animate-spin text-jarvis-blue" />;
      default: return <Clock className="text-gray-500" />;
    }
  };

  const getAgentIcon = (agentId?: string) => {
      switch (agentId) {
          case 'developer': return <FileCode className="w-5 h-5 text-jarvis-cyan" />;
          case 'operations': return <Terminal className="w-5 h-5 text-jarvis-violet" />;
          case 'qa_security': return <ShieldAlert className="w-5 h-5 text-red-400" />;
          case 'communications': return <MessageSquare className="w-5 h-5 text-green-400" />;
          case 'research': return <Briefcase className="w-5 h-5 text-yellow-400" />;
          default: return <Cpu className="w-5 h-5 text-gray-400" />;
      }
  };

  const selectedTask = tasks.find(t => t.task_id === selectedTaskId) || null;

  let coreState: CoreState = 'IDLE';
  if (selectedTask) {
      if (['queued', 'planning'].includes(selectedTask.status)) coreState = 'THINKING';
      else if (['running', 'verifying'].includes(selectedTask.status)) coreState = 'EXECUTING';
      else if (selectedTask.status === 'waiting_for_approval') coreState = 'WAITING';
      else if (selectedTask.status === 'succeeded') coreState = 'SUCCESS';
      else if (selectedTask.status === 'failed') coreState = 'FAILED';
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-jarvis-dark text-gray-100 font-sans">

      {/* SIDEBAR */}
      <motion.aside
        initial={{ x: -300 }}
        animate={{ x: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="w-72 bg-jarvis-panel border-r border-jarvis-border flex flex-col z-20"
      >
        <div className="p-6 border-b border-jarvis-border flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-jarvis-dark border border-jarvis-cyan flex items-center justify-center orb-glow">
             <Zap className="w-4 h-4 text-jarvis-cyan" />
          </div>
          <h1 className="text-xl font-bold tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400">JARVIS OS</h1>
        </div>

        <div className="p-4">
          <input
              type="password"
              placeholder="API Key (optional)"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              className="w-full bg-jarvis-surface border border-jarvis-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-jarvis-cyan transition-colors"
          />
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Task History</h2>
            <AnimatePresence>
                {tasks.map(task => (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, height: 0 }}
                    key={task.task_id}
                    onClick={() => setSelectedTaskId(task.task_id)}
                    className={`p-3 rounded-lg cursor-pointer flex items-center gap-3 transition-all ${
                        selectedTaskId === task.task_id
                            ? 'bg-jarvis-surface border border-jarvis-cyan/30 shadow-[0_0_10px_rgba(6,182,212,0.1)]'
                            : 'hover:bg-jarvis-surface border border-transparent'
                    }`}
                >
                    <div className="shrink-0">{getStatusIcon(task.status)}</div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{task.description}</p>
                        <p className="text-xs text-gray-500 uppercase">{task.status.replace(/_/g, ' ')}</p>
                    </div>
                </motion.div>
                ))}
            </AnimatePresence>
        </div>
      </motion.aside>

      {/* MAIN WORKSPACE */}
      <main className="flex-1 flex flex-col relative overflow-hidden bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-jarvis-panel to-jarvis-dark">

          {/* HEADER COMPOSER */}
          <div className="p-8 border-b border-jarvis-border bg-jarvis-panel/50 backdrop-blur-md z-30 relative">
              <form onSubmit={submitTask} className="max-w-4xl mx-auto relative group">
                  <div className="absolute -inset-1 bg-gradient-to-r from-jarvis-cyan to-jarvis-violet rounded-2xl opacity-20 group-hover:opacity-40 transition-opacity blur"></div>
                  <div className="relative flex bg-jarvis-dark border border-jarvis-border rounded-xl overflow-hidden focus-within:border-jarvis-cyan transition-colors shadow-2xl">
                      <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Assign a task to JARVIS..."
                        className="flex-1 bg-transparent px-6 py-4 text-lg focus:outline-none placeholder-gray-500"
                      />
                      <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="px-6 flex items-center justify-center bg-jarvis-surface hover:bg-jarvis-cyan hover:text-jarvis-dark disabled:opacity-50 disabled:hover:bg-jarvis-surface disabled:hover:text-gray-100 transition-colors border-l border-jarvis-border font-medium"
                      >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                      </button>
                  </div>

                  <div className="flex gap-2 mt-4 text-xs text-gray-400">
                      <span className="px-2 py-1 bg-jarvis-surface rounded-md cursor-pointer hover:text-white" onClick={() => setInput("Deploy to production")}>Deploy to production</span>
                      <span className="px-2 py-1 bg-jarvis-surface rounded-md cursor-pointer hover:text-white" onClick={() => setInput("Run a security scan on the workspace")}>Run a security scan on the workspace</span>
                      <span className="px-2 py-1 bg-jarvis-surface rounded-md cursor-pointer hover:text-white" onClick={() => setInput("Research information about LangGraph")}>Research information about LangGraph</span>
                  </div>
              </form>
          </div>

          {/* TASK VIEW */}
          <div className="flex-1 overflow-auto p-8 relative z-10 flex flex-col h-full">
              {selectedTask ? (
                  <motion.div
                      key={selectedTask.task_id}
                      initial={{ opacity: 0, scale: 0.98 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="max-w-7xl mx-auto flex flex-col xl:flex-row gap-8 w-full h-full"
                  >
                      {/* Left Panel: Primary Content */}
                      <div className="flex-1 flex flex-col glass-panel overflow-hidden h-full">
                          <div className="p-6 border-b border-jarvis-border flex justify-between items-center bg-jarvis-surface/50">
                              <h2 className="text-xl font-medium truncate pr-4">{selectedTask.description}</h2>
                              <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-jarvis-dark border border-jarvis-border shrink-0">
                                  {getStatusIcon(selectedTask.status)}
                                  <span className="text-sm font-medium uppercase tracking-wider">{selectedTask.status.replace(/_/g, ' ')}</span>
                              </div>
                          </div>

                          <div className="flex border-b border-jarvis-border bg-jarvis-dark overflow-x-auto shrink-0">
                              {['overview', 'activity', 'results', 'logs'].map(tab => (
                                  <button
                                      key={tab}
                                      onClick={() => setActiveTab(tab as any)}
                                      className={`px-6 py-3 text-sm font-medium transition-colors border-b-2 whitespace-nowrap ${activeTab === tab ? 'border-jarvis-cyan text-white bg-jarvis-surface/30' : 'border-transparent text-gray-500 hover:text-gray-300'}`}
                                  >
                                      {tab.charAt(0).toUpperCase() + tab.slice(1)}
                                  </button>
                              ))}
                          </div>

                          <div className="p-6 flex-1 overflow-y-auto">
                              {activeTab === 'overview' && (
                                  <div className="space-y-6">
                                      <div className="p-4 rounded-lg bg-jarvis-dark border border-jarvis-border">
                                          <h3 className="text-sm text-gray-500 mb-2">Task ID</h3>
                                          <p className="font-mono text-sm">{selectedTask.task_id}</p>
                                      </div>

                                      {selectedTask.error && (
                                          <div className="p-4 rounded-lg bg-red-950/30 border border-red-500/50 text-red-200">
                                              <h3 className="text-sm text-red-500 font-bold mb-2">Error Encountered</h3>
                                              <pre className="whitespace-pre-wrap text-sm font-mono">{selectedTask.error}</pre>
                                          </div>
                                      )}

                                      {selectedTask.result && (
                                          <div className="p-4 rounded-lg bg-jarvis-dark border border-jarvis-border">
                                              <h3 className="text-sm text-jarvis-cyan font-bold mb-2">Final Output</h3>
                                              <pre className="whitespace-pre-wrap text-sm font-mono text-gray-300">{selectedTask.result}</pre>
                                          </div>
                                      )}

                                      {selectedTask.status !== 'succeeded' && selectedTask.status !== 'failed' && selectedTask.status !== 'cancelled' && (
                                          <button
                                              onClick={() => cancelTask(selectedTask.task_id)}
                                              className="mt-4 px-4 py-2 border border-red-500/50 text-red-400 hover:bg-red-500 hover:text-white rounded-lg transition-colors flex items-center gap-2 text-sm"
                                          >
                                              <X className="w-4 h-4" /> Cancel Task Execution
                                          </button>
                                      )}
                                  </div>
                              )}

                              {activeTab === 'activity' && (
                                  <div className="space-y-4">
                                      {selectedTask.history && selectedTask.history.length > 0 ? (
                                          selectedTask.history.map((h, i) => (
                                              <div key={i} className="p-4 rounded-lg bg-jarvis-dark border border-jarvis-border border-l-4 border-l-jarvis-blue">
                                                  {h.pending_action && (
                                                      <div>
                                                          <p className="text-sm font-bold text-yellow-500">Requested Approval: {h.pending_action.action}</p>
                                                          <p className="text-xs font-mono mt-1 text-gray-400">{h.pending_action.target}</p>
                                                      </div>
                                                  )}
                                                  {h.approved_action && (
                                                       <p className="text-sm font-bold text-green-500">Approval Resolved: {h.approved_action}</p>
                                                  )}
                                                  {/* General placeholder for MVP backend execution history */}
                                                  {!h.pending_action && !h.approved_action && (
                                                       <p className="text-sm text-gray-300">Execution context snapshot recorded.</p>
                                                  )}
                                              </div>
                                          ))
                                      ) : (
                                          <p className="text-gray-500 text-sm italic">No activity history recorded.</p>
                                      )}
                                  </div>
                              )}

                              {(activeTab === 'results' || activeTab === 'logs') && (
                                  <div className="flex items-center justify-center h-full text-gray-500 text-center px-4">
                                      <p>The backend does not currently stream live individual execution events or manifest artifacts for this view.</p>
                                  </div>
                              )}
                          </div>
                      </div>

                      {/* Right Panel: Agent Orchestration & Approvals */}
                      <div className="w-full xl:w-96 flex flex-col gap-6 shrink-0 h-full overflow-y-auto pr-2 pb-2">

                          {/* Orchestration View */}
                          <div className="glass-panel p-5 overflow-hidden flex flex-col">
                              <h3 className="text-sm font-bold uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
                                  <Workflow className="w-4 h-4" /> Orchestration Graph
                              </h3>

                              <div className="relative mb-6">
                                  <AgentGraph activeAgentId={selectedTask.agent_id} status={selectedTask.status} />
                              </div>

                              <div className="flex items-center gap-4 p-4 bg-jarvis-dark border border-jarvis-border rounded-lg mt-auto">
                                  <div className="w-10 h-10 rounded-full bg-jarvis-surface flex items-center justify-center shrink-0">
                                      {getAgentIcon(selectedTask.agent_id)}
                                  </div>
                                  <div className="min-w-0">
                                      <p className="font-medium capitalize truncate">{selectedTask.agent_id ? selectedTask.agent_id.replace('_', ' ') : 'Supervisor'}</p>
                                      <p className="text-xs text-gray-400 capitalize truncate">{selectedTask.status.replace('_', ' ')}</p>
                                  </div>
                              </div>
                          </div>

                          {selectedTask.status === 'waiting_for_approval' && selectedTask.history && (
                              <motion.div
                                  initial={{ opacity: 0, y: 20 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  className="glass-panel border-yellow-500/50 bg-yellow-950/20 p-5 shadow-[0_0_15px_rgba(234,179,8,0.1)] shrink-0"
                              >
                                  <h3 className="text-sm font-bold uppercase tracking-wider text-yellow-500 mb-2 flex items-center gap-2">
                                      <ShieldAlert className="w-4 h-4" /> Action Required
                                  </h3>

                                  {(() => {
                                      const lastReq = selectedTask.history.slice().reverse().find(h => h.pending_action);
                                      if (!lastReq) return <p className="text-sm">Unknown approval state.</p>;
                                      return (
                                          <>
                                            <p className="text-sm text-gray-300 mb-4">The agent is requesting permission to execute:</p>
                                            <div className="p-3 bg-jarvis-dark border border-yellow-500/30 rounded text-sm font-mono text-yellow-200 mb-4 break-all max-h-40 overflow-y-auto">
                                                {lastReq.pending_action?.action}
                                                <br/>
                                                <span className="text-xs text-gray-500">{lastReq.pending_action?.target}</span>
                                            </div>

                                            <div className="flex gap-2">
                                                <button onClick={() => resolveApproval(selectedTask, 'approve')} className="flex-1 bg-jarvis-cyan hover:bg-cyan-400 text-jarvis-dark font-bold py-2 rounded transition-colors flex justify-center items-center gap-2">
                                                    <CheckSquare className="w-4 h-4" /> Approve
                                                </button>
                                                <button onClick={() => resolveApproval(selectedTask, 'reject')} className="flex-1 bg-transparent hover:bg-red-500/20 border border-red-500/50 text-red-500 font-bold py-2 rounded transition-colors">
                                                    Reject
                                                </button>
                                            </div>
                                          </>
                                      );
                                  })()}
                              </motion.div>
                          )}

                      </div>
                  </motion.div>
              ) : (
                  <div className="h-full flex flex-col items-center justify-center opacity-50 select-none absolute inset-0">
                      <JarvisCore state={coreState} />
                      <h2 className="text-2xl font-bold text-gray-600 mt-8 tracking-widest uppercase">JARVIS OS</h2>
                      <p className="text-gray-500 mt-2 tracking-widest text-sm">Awaiting Instructions.</p>
                  </div>
              )}
          </div>
      </main>
    </div>
  );
}
