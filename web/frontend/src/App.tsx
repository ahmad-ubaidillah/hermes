// Aizen Agent Dashboard - Black & White Minimal
// FastAPI + React + TypeScript

import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

interface Agent {
  name: string;
  role: string;
  status: 'idle' | 'busy' | 'error';
  current_task: string | null;
  tasks_completed: number;
  tokens_used: number;
}

interface Task {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'in_progress' | 'done' | 'blocked';
  assignee: string | null;
  priority: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
}

interface Stats {
  total_agents: number;
  active_agents: number;
  total_tasks: number;
  completed_tasks: number;
  total_tokens: number;
  remaining_budget: number;
}

// ─────────────────────────────────────────────────────────────
// Styles (inline for single-file simplicity)
// ─────────────────────────────────────────────────────────────

const styles = {
  page: {
    backgroundColor: '#000',
    color: '#fff',
    minHeight: '100vh',
    fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
    padding: '0',
  },
  header: {
    borderBottom: '1px solid #333',
    padding: '1.5rem 2rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  logo: {
    fontSize: '1.5rem',
    fontWeight: 'bold' as const,
    letterSpacing: '0.1em',
  },
  container: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '2rem',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '1.5rem',
  },
  card: {
    backgroundColor: '#111',
    border: '1px solid #333',
    borderRadius: '8px',
    padding: '1.5rem',
  },
  cardTitle: {
    fontSize: '0.75rem',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.1em',
    color: '#666',
    marginBottom: '0.5rem',
  },
  cardValue: {
    fontSize: '2rem',
    fontWeight: 'bold' as const,
  },
  statusDot: {
    display: 'inline-block',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    marginRight: '0.5rem',
  },
  taskCard: {
    backgroundColor: '#0a0a0a',
    border: '1px solid #222',
    borderRadius: '4px',
    padding: '1rem',
    marginBottom: '0.75rem',
  },
  column: {
    backgroundColor: '#0a0a0a',
    border: '1px solid #222',
    borderRadius: '8px',
    padding: '1rem',
  },
  columnTitle: {
    fontSize: '0.75rem',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.1em',
    color: '#666',
    marginBottom: '1rem',
    paddingBottom: '0.5rem',
    borderBottom: '1px solid #222',
  },
};

// ─────────────────────────────────────────────────────────────
// Components
// ─────────────────────────────────────────────────────────────

const StatusDot: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = {
    idle: '#666',
    busy: '#fff',
    error: '#f00',
    done: '#0f0',
    in_progress: '#fff',
    todo: '#666',
    blocked: '#f00',
  };
  return (
    <span style={{ ...styles.statusDot, backgroundColor: colors[status] || '#666' }} />
  );
};

const AgentCard: React.FC<{ agent: Agent }> = ({ agent }) => (
  <div style={styles.card}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div>
        <div style={styles.cardTitle}>{agent.role}</div>
        <div style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>{agent.name}</div>
      </div>
      <StatusDot status={agent.status} />
    </div>
    <div style={{ marginTop: '1rem', fontSize: '0.875rem', color: '#888' }}>
      {agent.current_task && <div>▸ {agent.current_task}</div>}
      <div style={{ marginTop: '0.5rem' }}>
        ✓ {agent.tasks_completed} tasks · {agent.tokens_used.toLocaleString()} tokens
      </div>
    </div>
  </div>
);

const TaskCard: React.FC<{ task: Task }> = ({ task }) => (
  <div style={styles.taskCard}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <div style={{ fontWeight: '500' }}>{task.title}</div>
      <div style={{ fontSize: '0.625rem', textTransform: 'uppercase', color: '#666' }}>
        {task.priority}
      </div>
    </div>
    {task.description && (
      <div style={{ fontSize: '0.875rem', color: '#888', marginTop: '0.5rem' }}>
        {task.description}
      </div>
    )}
    <div style={{ fontSize: '0.75rem', color: '#555', marginTop: '0.75rem' }}>
      {task.assignee || 'Unassigned'}
    </div>
  </div>
);

const StatCard: React.FC<{ label: string; value: string | number; highlight?: boolean }> = 
  ({ label, value, highlight }) => (
  <div style={styles.card}>
    <div style={styles.cardTitle}>{label}</div>
    <div style={{ ...styles.cardValue, color: highlight ? '#0f0' : '#fff' }}>{value}</div>
  </div>
);

const KanbanColumn: React.FC<{ title: string; tasks: Task[] }> = ({ title, tasks }) => (
  <div style={styles.column}>
    <div style={styles.columnTitle}>
      {title} <span style={{ color: '#444' }}>({tasks.length})</span>
    </div>
    {tasks.map(task => <TaskCard key={task.id} task={task} />)}
  </div>
);

// ─────────────────────────────────────────────────────────────
// Main App
// ─────────────────────────────────────────────────────────────

const App: React.FC = () => {
  const [stats, setStats] = useState<Stats>({
    total_agents: 0,
    active_agents: 0,
    total_tasks: 0,
    completed_tasks: 0,
    total_tokens: 0,
    remaining_budget: 0,
  });
  
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, agentsRes, tasksRes] = await Promise.all([
          axios.get(`${API_URL}/stats`),
          axios.get(`${API_URL}/agents`),
          axios.get(`${API_URL}/tasks`),
        ]);
        setStats(statsRes.data);
        setAgents(agentsRes.data);
        setTasks(tasksRes.data);
      } catch (error) {
        // Use demo data if API not available
        setStats({
          total_agents: 5,
          active_agents: 3,
          total_tasks: 12,
          completed_tasks: 7,
          total_tokens: 125000,
          remaining_budget: 50000,
        });
        setAgents([
          { name: 'Atlas', role: 'Architect', status: 'busy', current_task: 'Designing API', tasks_completed: 15, tokens_used: 45000 },
          { name: 'Cody', role: 'Developer', status: 'busy', current_task: 'Implementing auth', tasks_completed: 23, tokens_used: 52000 },
          { name: 'Nova', role: 'PM', status: 'idle', current_task: null, tasks_completed: 8, tokens_used: 18000 },
          { name: 'Testa', role: 'QA', status: 'idle', current_task: null, tasks_completed: 12, tokens_used: 10000 },
        ]);
        setTasks([
          { id: '1', title: 'Setup authentication', description: 'Implement JWT auth', status: 'in_progress', assignee: 'Cody', priority: 'high', created_at: new Date().toISOString() },
          { id: '2', title: 'Design database schema', description: 'Create ERD for users', status: 'done', assignee: 'Atlas', priority: 'high', created_at: new Date().toISOString() },
          { id: '3', title: 'Write unit tests', description: 'Coverage for auth module', status: 'todo', assignee: 'Testa', priority: 'medium', created_at: new Date().toISOString() },
          { id: '4', title: 'API documentation', description: 'OpenAPI spec', status: 'todo', assignee: 'Nova', priority: 'low', created_at: new Date().toISOString() },
        ]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div style={{ ...styles.page, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>&lt;z&gt;</div>
          <div style={{ color: '#666' }}>Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.logo}>
          &lt;z&gt; AIZEN AGENT
        </div>
        <div style={{ fontSize: '0.75rem', color: '#666' }}>
          Execute with Zen
        </div>
      </header>

      {/* Stats */}
      <div style={styles.container}>
        <div style={{ ...styles.grid, marginBottom: '2rem' }}>
          <StatCard label="Active Agents" value={`${stats.active_agents}/${stats.total_agents}`} />
          <StatCard label="Tasks Done" value={`${stats.completed_tasks}/${stats.total_tasks}`} />
          <StatCard label="Tokens Used" value={`${(stats.total_tokens / 1000).toFixed(1)}K`} />
          <StatCard label="Budget Left" value={`${(stats.remaining_budget / 1000).toFixed(0)}K`} highlight />
        </div>

        {/* Agents */}
        <div style={{ marginBottom: '2rem' }}>
          <div style={styles.columnTitle}>AGENTS</div>
          <div style={styles.grid}>
            {agents.map(agent => <AgentCard key={agent.name} agent={agent} />)}
          </div>
        </div>

        {/* Kanban */}
        <div>
          <div style={styles.columnTitle}>TASKS</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
            <KanbanColumn title="TODO" tasks={tasks.filter(t => t.status === 'todo')} />
            <KanbanColumn title="IN PROGRESS" tasks={tasks.filter(t => t.status === 'in_progress')} />
            <KanbanColumn title="DONE" tasks={tasks.filter(t => t.status === 'done')} />
            <KanbanColumn title="BLOCKED" tasks={tasks.filter(t => t.status === 'blocked')} />
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid #333', padding: '1rem 2rem', textAlign: 'center', color: '#444', fontSize: '0.75rem' }}>
        Assign. Review. Repeat.
      </footer>
    </div>
  );
};

export default App;
