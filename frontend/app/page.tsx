'use client';

import { useEffect, useState } from 'react';

interface Task {
  title: string;
  status: string;
}

export default function Home() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTitle, setNewTitle] = useState('');
  const [authHealth, setAuthHealth] = useState('Vérification...');
  const [taskHealth, setTaskHealth] = useState('Vérification...');

  const AUTH_API = 'http://localhost:8001';
  const TASK_API = 'http://localhost:8002';

  const fetchTasks = async () => {
    try {
      const res = await fetch(`${TASK_API}/tasks/`);
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      }
    } catch (err) {
      console.error('Erreur lors de la récupération des tâches:', err);
    }
  };

  useEffect(() => {
    fetch(`${AUTH_API}/health`)
      .then((res) => res.json())
      .then((d) => setAuthHealth(d.status || 'ok'))
      .catch(() => setAuthHealth('Hors ligne'));

    fetch(`${TASK_API}/health`)
      .then((res) => res.json())
      .then((d) => setTaskHealth(d.status || 'ok'))
      .catch(() => setTaskHealth('Hors ligne'));

    fetchTasks();
  }, []);

  const addTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    try {
      const res = await fetch(`${TASK_API}/tasks/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle, status: 'todo' }),
      });

      if (res.ok) {
        setNewTitle('');
        fetchTasks();
      }
    } catch (err) {
      console.error('Erreur lors de l’ajout:', err);
    }
  };

  return (
    <main style={{ padding: '2rem', fontFamily: 'sans-serif', maxWidth: '600px', margin: '0 auto' }}>
      <h1>Vérification US05 - Application 3-Tiers</h1>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
        <div
          style={{
            padding: '0.5rem 1rem',
            background: authHealth === 'ok' ? '#d4edda' : '#f8d7da',
            borderRadius: '4px',
          }}
        >
          <strong>Auth Service (8001):</strong> {authHealth}
        </div>
        <div
          style={{
            padding: '0.5rem 1rem',
            background: taskHealth === 'ok' ? '#d4edda' : '#f8d7da',
            borderRadius: '4px',
          }}
        >
          <strong>Task Service (8002):</strong> {taskHealth}
        </div>
      </div>

      <form onSubmit={addTask} style={{ marginBottom: '2rem', display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          placeholder="Nouvelle tâche..."
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          style={{ flex: 1, padding: '0.5rem' }}
        />
        <button type="submit" style={{ padding: '0.5rem 1rem', cursor: 'pointer' }}>
          Ajouter
        </button>
      </form>

      <h2>Tâches persistées en MongoDB ({tasks.length})</h2>
      <ul>
        {tasks.map((task, idx) => (
          <li key={idx} style={{ margin: '0.5rem 0' }}>
            {task.title} <span style={{ color: '#666', fontSize: '0.85rem' }}>({task.status})</span>
          </li>
        ))}
      </ul>
    </main>
  );
}