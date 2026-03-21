import React, { useState, useEffect } from 'react';

// Live countdown to next scheduled run
function useCountdown(targetISO) {
  const [label, setLabel] = useState('—');
  useEffect(() => {
    if (!targetISO) { setLabel('—'); return; }
    const tick = () => {
      const diff = new Date(targetISO) - Date.now();
      if (diff <= 0) { setLabel('Now'); return; }
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      setLabel(`${h}h ${m}m`);
    };
    tick();
    const id = setInterval(tick, 30000);
    return () => clearInterval(id);
  }, [targetISO]);
  return label;
}

const Dashboard = () => {
  const [queue, setQueue] = useState([]);
  const [stats, setStats] = useState({
    totalVideos: 0,
    subscribers: 0,
    avgCompletion: "0%",
    views: 0,
    channelName: "Loading..."
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [publishingTopicId, setPublishingTopicId] = useState(null);
  const [selectedStream, setSelectedStream] = useState('BTech');
  const [pipelineLog, setPipelineLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [serverError, setServerError] = useState(null);

  // Auto-Pilot
  const [autoPilot, setAutoPilot] = useState(null);
  const [apStream, setApStream] = useState('BTech');
  const [apHour, setApHour] = useState(18);
  const countdown = useCountdown(autoPilot?.nextRun);

  const fetchDashboardData = async () => {
    try {
      const statsRes = await fetch('http://localhost:3001/api/stats');
      if (statsRes.ok) setStats(await statsRes.json());

      const queueRes = await fetch('http://localhost:3001/api/queue');
      if (queueRes.ok) setQueue(await queueRes.json());

      const apRes = await fetch('http://localhost:3001/api/scheduler/status');
      if (apRes.ok) {
        const apData = await apRes.json();
        setAutoPilot(apData);
        setApStream(apData.stream || 'BTech');
        setApHour(apData.uploadHourIST ?? 18);
      }
      setServerError(null);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
      setServerError("Backend API server is offline. Please run 'node core/server.js' in the terminal.");
    } finally {
      setLoading(false);
    }
  };

  const fetchLogs = async () => {
    try {
      const logsRes = await fetch('http://localhost:3001/api/pipeline-logs');
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setPipelineLog(logsData.logs || []);
      }
    } catch (e) {
      // Ignore log fetch errors to prevent spamming console if server drops
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const dataInterval = setInterval(fetchDashboardData, 30000); // 30s Notion/YT polling
    const logsInterval = setInterval(fetchLogs, 2000); // 2s Real-time logs polling
    return () => {
      clearInterval(dataInterval);
      clearInterval(logsInterval);
    };
  }, []);

  useEffect(() => {
    // If we're processing or publishing, check if logs indicate completion or failure
    if ((isProcessing || publishingTopicId) && pipelineLog.length > 0) {
      const latestLogs = pipelineLog.slice(-5).join('\n').toLowerCase();
      if (latestLogs.includes('pipeline complete!') || latestLogs.includes('pipeline error')) {
         setIsProcessing(false);
         setPublishingTopicId(null);
      }
    }
  }, [pipelineLog]);

  // ── Publish: Next Pending (by stream) ──────────────────────────────
  const startPipeline = async () => {
    setIsProcessing(true);
    try {
      await fetch('http://localhost:3001/api/run-pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stream: selectedStream })
      });
    } catch (error) {
      console.error("Error starting pipeline:", error);
      setIsProcessing(false);
    }
  };

  // ── Publish: Specific Topic ────────────────────────────────────────
  const publishTopic = async (item) => {
    setPublishingTopicId(item.id);
    try {
      await fetch('http://localhost:3001/api/run-pipeline-topic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pageId: item.id,
          topic: item.topic,
          subject: item.subject,
          chapter: item.chapter,
          stream: item.stream
        })
      });
    } catch (error) {
      console.error("Failed to publish", error);
      setPublishingTopicId(null);
    }
  };

  // ── Auto-Pilot: Enable / Disable ──────────────────────────────────
  const enableAutoPilot = async () => {
    const res = await fetch('http://localhost:3001/api/scheduler/enable', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stream: apStream, uploadHourIST: apHour })
    });
    if (res.ok) setAutoPilot(await res.json());
  };

  const disableAutoPilot = async () => {
    const res = await fetch('http://localhost:3001/api/scheduler/disable', { method: 'POST' });
    if (res.ok) setAutoPilot(await res.json());
  };

  if (loading) {
    return (
      <div className="dashboard-container" style={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh'}}>
        <h2>Loading Live EduContent Data...</h2>
      </div>
    );
  }

  if (serverError) {
    return (
      <div className="dashboard-container" style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100vh'}}>
        <h2 style={{color: 'var(--warning)', marginBottom: '1rem'}}>⚠️ Connection Lost</h2>
        <p>{serverError}</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <h1>{stats.channelName} Command Center</h1>
      
      {/* ── Stats Row ─────────────────────────────────────────── */}
      <div className="grid-layout">
        <div className="glass-panel stat-card">
          <span className="stat-label">Total Videos Generated</span>
          <span className="stat-value">{stats.totalVideos}</span>
        </div>
        <div className="glass-panel stat-card">
          <span className="stat-label">Channel Subscribers</span>
          <span className="stat-value" style={{color: 'var(--success)'}}>{stats.subscribers}</span>
        </div>
        <div className="glass-panel stat-card">
          <span className="stat-label">Total Channel Views</span>
          <span className="stat-value">{stats.views}</span>
        </div>
      </div>

      {/* ── Queue + Insights ──────────────────────────────────── */}
      <div className="grid-layout">
        <div className="glass-panel">
          <h2>🎯 Video Queue (Live from Notion)</h2>
          {queue.length === 0 ? (
            <p>No remaining videos in the queue!</p>
          ) : (
            <ul className="queue-list">
              {queue.map((item) => (
                <li key={item.id} className="queue-item">
                  <div style={{flex: 1}}>
                    <strong>{item.topic}</strong>
                    <p style={{fontSize: '0.85rem'}}>{item.subject} | {item.chapter} | {item.stream}</p>
                  </div>
                  <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
                    <span className={`badge ${item.status === 'Pending' ? 'pending' : 'success'}`}>
                      {item.status}
                    </span>
                    {item.status === 'Pending' && (
                      <button
                        className={`btn btn-publish ${publishingTopicId === item.id ? 'pulse' : ''}`}
                        onClick={() => publishTopic(item)}
                        disabled={publishingTopicId === item.id}
                        title={`Publish "${item.topic}" to YouTube`}
                      >
                        {publishingTopicId === item.id ? '⏳' : '🚀'}
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="glass-panel">
          <h2>💡 Pipeline Activity</h2>
          {pipelineLog.length === 0 ? (
            <div className="insights-list">
              <div className="insight-card success">
                <strong>Ready</strong>
                <p>Pipeline is idle. Use the Publish button to start processing videos.</p>
              </div>
              <div className="insight-card">
                <strong>SEO Engine</strong>
                <p>Viral title generator active — titles rotate through 12 attention-grabbing formulas.</p>
              </div>
            </div>
          ) : (
            <div className="pipeline-log" style={{ maxHeight: '250px', overflowY: 'auto' }}>
              {pipelineLog.slice(-15).map((log, i) => (
                <div key={i} className="log-entry" style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                  <span>{log}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Publish Control Panel ─────────────────────────────── */}
      <div className="glass-panel publish-control-panel">
        <div style={{flex: 1}}>
          <h2>🚀 Publish Next Video</h2>
          <p>Auto-picks the next "Pending" topic from Notion, generates video via NotebookLM, applies TTS voice clone, creates thumbnail, and publishes to YouTube.</p>
        </div>
        <div className="publish-controls">
          <select
            className="stream-select"
            value={selectedStream}
            onChange={(e) => setSelectedStream(e.target.value)}
          >
            <option value="BTech">BTech</option>
            <option value="MBBS">MBBS</option>
          </select>
          <button
            className={`btn btn-primary btn-large ${isProcessing ? 'pulse' : ''}`}
            onClick={startPipeline}
            disabled={isProcessing}
          >
            {isProcessing ? '⏳ Pipeline Running...' : '🚀 Publish'}
          </button>
        </div>
      </div>

      {/* ── Auto-Pilot Panel ──────────────────────────────────── */}
      <div className="glass-panel" style={{ borderLeft: autoPilot?.enabled ? '4px solid var(--success)' : '4px solid rgba(255,255,255,0.1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.2rem' }}>
          <h2 style={{ margin: 0 }}>🤖 Auto-Pilot</h2>
          <span style={{
            padding: '4px 14px', borderRadius: '20px', fontSize: '0.8rem', fontWeight: 700,
            background: autoPilot?.enabled ? 'rgba(16,185,129,0.2)' : 'rgba(255,255,255,0.07)',
            color: autoPilot?.enabled ? 'var(--success)' : '#94a3b8',
            border: `1px solid ${autoPilot?.enabled ? 'var(--success)' : 'rgba(255,255,255,0.1)'}`,
          }}>
            {autoPilot?.enabled ? 'ENABLED' : 'DISABLED'}
          </span>
        </div>

        {autoPilot?.enabled ? (
          <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
            {/* Status cards */}
            <div style={{ flex: 1, minWidth: '160px' }}>
              <p style={{ margin: '0 0 4px', fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8' }}>Next Upload In</p>
              <p style={{ margin: 0, fontSize: '2rem', fontWeight: 700, color: 'var(--success)' }}>{countdown}</p>
              <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: '#64748b' }}>{autoPilot.nextRunFormatted || '—'}</p>
            </div>
            <div style={{ flex: 1, minWidth: '160px' }}>
              <p style={{ margin: '0 0 4px', fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8' }}>Schedule</p>
              <p style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>{autoPilot.uploadHourIST}:00 IST · {autoPilot.stream}</p>
            </div>
            <div style={{ flex: 1, minWidth: '160px' }}>
              <p style={{ margin: '0 0 4px', fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8' }}>Last Run</p>
              <p style={{ margin: 0, fontSize: '0.95rem' }}>{autoPilot.lastRunFormatted || 'Never'}</p>
              {autoPilot.lastStatus && (
                <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: autoPilot.lastStatus === 'success' ? 'var(--success)' : '#f59e0b' }}>
                  {autoPilot.lastStatus === 'success' ? '✓ Success' : autoPilot.lastStatus}
                </p>
              )}
            </div>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <button className="btn" onClick={disableAutoPilot}
                style={{ background: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' }}>
                Disable
              </button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
            <p style={{ flex: 1, margin: 0, color: '#94a3b8', minWidth: '200px' }}>
              Publish one video per day automatically. The pipeline picks the next Pending topic from Notion, generates the full video, and uploads to YouTube — no manual action needed.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <select className="stream-select" value={apStream} onChange={e => setApStream(e.target.value)}>
                <option value="BTech">BTech</option>
                <option value="MBBS">MBBS</option>
              </select>
              <select className="stream-select" value={apHour} onChange={e => setApHour(Number(e.target.value))}
                title="Upload time in IST">
                {Array.from({ length: 24 }, (_, h) => (
                  <option key={h} value={h}>
                    {h === 0 ? '12:00 AM' : h < 12 ? `${h}:00 AM` : h === 12 ? '12:00 PM' : `${h - 12}:00 PM`} IST
                  </option>
                ))}
              </select>
              <button className="btn btn-primary" onClick={enableAutoPilot}>
                Enable Auto-Pilot
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
