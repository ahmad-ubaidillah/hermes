// Hermes Dashboard - Main React App
// FastAPI + React + TypeScript

import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

// Types
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

// Components

const AgentCard: React.FC<{ agent: Agent }> = ({ agent }) => {
  const statusColor = {
    idle: 'bg-green-500',
    busy: 'bg-yellow-500',
    error: 'bg-red-500',
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-bold text-lg">{agent.name}</h3>
          <p className="text-gray-500 text-sm">{agent.role}</p>
        </div>
        <div className={`w-3 h-3 rounded-full ${statusColor[agent.status]}`} />
      </div>
      <div className="mt-3 text-sm">
        <p>Status: <span className="font-medium">{agent.status}</span></p>
        {agent.current_task && (
          <p>Task: <span className="font-mono">{agent.current_task}</span></p>
        )}
        <p>Completed: {agent.tasks_completed} | Tokens: {agent.tokens_used.toLocaleString()}</p>
      </div>
    </div>
  );
};

const TaskCard: React.FC<{ task: Task }> = ({ task }) => {
  const statusColors = {
    todo: 'bg-gray-100 border-gray-300',
    in_progress: 'bg-blue-50 border-blue-300',
    done: 'bg-green-50 border-green-300',
    blocked: 'bg-red-50 border-red-300',
  };

  const priorityBadge = {
    low: 'bg-gray-200 text-gray-700',
    medium: 'bg-blue-200 text-blue-700',
    high: 'bg-orange-200 text-orange-700',
    critical: 'bg-red-200 text-red-700',
  };

  return (
    <div className={`rounded-lg border p-3 ${statusColors[task.status]}`}>
      <div className="flex items-start justify-between">
        <h4 className="font-medium">{task.title}</h4>
        <span className={`px-2 py-1 rounded text-xs font-medium ${priorityBadge[task.priority]}`}>
          {task.priority}
        </span>
      </div>
      {task.description && (
        <p className="text-gray-600 text-sm mt-1">{task.description}</p>
      )}
      <div className="mt-2 flex items-center justify-between text-xs">
        <span className="text-gray-500">{task.assignee || 'Unassigned'}</span>
        <span className="text-gray-400">{task.status.replace('_', ' ')}</span>
      </div>
    </div>
  );
};

const StatsPanel: React.FC<{ stats: Stats }> = ({ stats }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      <div className="bg-white rounded-lg shadow p-4">
        <p className="text-gray-500 text-sm">Active Agents</p>
        <p className="text-2xl font-bold">{stats.active_agents}/{stats.total_agents}</p>
      </div>
      <div className="bg-white rounded-lg shadow p-4">
        <p className="text-gray-500 text-sm">Tasks</p>
        <p className="text-2xl font-bold">{stats.completed_tasks}/{stats.total_tasks}</p>
      </div>
      <div className="bg-white rounded-lg shadow p-4">
        <p className="text-gray-500 text-sm">Tokens Used</p>
        <p className="text-2xl font-bold">{(stats.total_tokens / 1000).toFixed(1)}K</p>
      </div>
      <div className="bg-white rounded-lg shadow p-4">
        <p className="text-gray-500 text-sm">Budget Remaining</p>
        <p className="text-2xl font-bold text-green-600">{(stats.remaining_budget / 1000).toFixed(0)}K</p>
      </div>
    </div>
  );
};

const KanbanBoard: React.FC<{ tasks: Task[] }> = ({ tasks }) => {
  const columns = ['todo', 'in_progress', 'done', 'blocked'];
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {columns.map(col => (
        <div key={col} className="bg-gray-50 rounded-lg p-3">
          <h3 className="font-medium mb-3 capitalize">{col.replace('_', ' ')}</h3>
          <div className="space-y-2">
            {tasks.filter(t => t.status === col).map(task => (
              <TaskCard key={task.id} task={task} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

// Main App

const App: React.FC = () => {
  const [stats, setStats] = useState<Stats>({
    total_agents: 0,
    active_agents: 0,
    total_tasks: 0,
    completed_tasks: 0,
    total_tokens: 0,
    remaining_budget: 550000,
  });
  
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

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
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Hermes Dashboard</h1>
          <p className="text-gray-500 text-sm">v3.0 - Autonomous AI Team</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Stats */}
        <StatsPanel stats={stats} />

        {/* Agents */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Agents</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {agents.map(agent => (
              <AgentCard key={agent.name} agent={agent} />
            ))}
          </div>
        </div>

        {/* Kanban Board */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Sprint Board</h2>
          <KanbanBoard tasks={tasks} />
        </div>
      </main>
    </div>
  );
};

export default App;
