import { motion } from 'framer-motion';
import { FileCode, Terminal, ShieldAlert, MessageSquare, Briefcase, Cpu } from 'lucide-react';

interface AgentGraphProps {
  activeAgentId?: string | null;
  status: string;
}

const AGENTS = [
  { id: 'research', label: 'Research', icon: Briefcase, color: '#facc15', angle: -Math.PI / 2 },
  { id: 'developer', label: 'Developer', icon: FileCode, color: '#06b6d4', angle: -Math.PI / 6 },
  { id: 'operations', label: 'Operations', icon: Terminal, color: '#8b5cf6', angle: Math.PI / 6 },
  { id: 'communications', label: 'Comms', icon: MessageSquare, color: '#4ade80', angle: Math.PI / 2 },
  { id: 'qa_security', label: 'QA / Sec', icon: ShieldAlert, color: '#f87171', angle: 5 * Math.PI / 6 },
];

export function AgentGraph({ activeAgentId, status }: AgentGraphProps) {
  const radius = 120;
  const center = { x: 200, y: 180 };

  return (
    <div className="relative w-full h-[360px] flex items-center justify-center">
      <svg width="400" height="360" className="absolute top-0 left-1/2 -translate-x-1/2 pointer-events-none">
        {/* Draw connections first so they are underneath */}
        {AGENTS.map((agent) => {
          const x = center.x + radius * Math.cos(agent.angle);
          const y = center.y + radius * Math.sin(agent.angle);
          const isActive = activeAgentId === agent.id;
          const isFailed = isActive && status === 'failed';

          return (
            <g key={`edge-${agent.id}`}>
              <line
                x1={center.x}
                y1={center.y}
                x2={x}
                y2={y}
                stroke={isActive ? (isFailed ? '#dc2626' : agent.color) : '#1E293B'}
                strokeWidth={isActive ? 2 : 1}
                strokeDasharray={isActive ? "4 4" : "none"}
                className={isActive ? "animate-pulse" : ""}
              />
              {/* Particles for active connection */}
              {isActive && status !== 'failed' && (
                <motion.circle
                  r="3"
                  fill={agent.color}
                  initial={{ cx: center.x, cy: center.y, opacity: 0 }}
                  animate={{ cx: x, cy: y, opacity: [0, 1, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                  style={{ filter: `drop-shadow(0 0 5px ${agent.color})` }}
                />
              )}
            </g>
          );
        })}
      </svg>

      {/* Center Supervisor Node */}
      <div
        className="absolute w-16 h-16 bg-jarvis-panel border-2 border-white/20 rounded-full flex flex-col items-center justify-center z-10"
        style={{ left: `calc(50% - 32px)`, top: center.y - 32 }}
      >
        <Cpu className={`w-6 h-6 ${!activeAgentId ? 'text-jarvis-cyan' : 'text-gray-400'}`} />
      </div>

      {/* Specialist Nodes */}
      {AGENTS.map((agent) => {
        const x = radius * Math.cos(agent.angle);
        const y = radius * Math.sin(agent.angle);
        const isActive = activeAgentId === agent.id;
        const isWaiting = isActive && status === 'waiting_for_approval';
        const isFailed = isActive && status === 'failed';

        let borderColor = 'border-jarvis-border';
        let bgClass = 'bg-jarvis-panel';

        if (isActive) {
            borderColor = `border-[${agent.color}]`;
            bgClass = 'bg-jarvis-surface';
            if (isWaiting) borderColor = 'border-yellow-500';
            if (isFailed) borderColor = 'border-red-500';
        }

        return (
          <motion.div
            key={agent.id}
            animate={{
                scale: isActive ? 1.15 : 1,
                boxShadow: isActive ? `0 0 20px ${isWaiting ? '#eab308' : isFailed ? '#dc2626' : agent.color}40` : 'none'
            }}
            className={`absolute flex flex-col items-center justify-center w-14 h-14 rounded-full border-2 ${borderColor} ${bgClass} z-20 transition-colors`}
            style={{
                left: `calc(50% + ${x}px - 28px)`,
                top: center.y + y - 28
            }}
            title={agent.label}
          >
            <agent.icon className="w-5 h-5" style={{ color: isActive ? (isWaiting ? '#eab308' : isFailed ? '#dc2626' : agent.color) : '#64748b' }} />
            <span className="absolute -bottom-6 text-[10px] uppercase font-bold tracking-wider whitespace-nowrap text-gray-400">
                {agent.label}
            </span>
          </motion.div>
        );
      })}
    </div>
  );
}
