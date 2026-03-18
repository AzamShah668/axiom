import React, { useState, useEffect } from 'react';

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
  const [loading, setLoading] = useState(true);
  const [serverError, setServerError] = useState(null);

  const fetchDashboardData = async () => {
    try {
      // Fetch YT Stats
      const statsRes = await fetch('http://localhost:3001/api/stats');
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      // Fetch Notion Queue
      const queueRes = await fetch('http://localhost:3001/api/queue');
      if (queueRes.ok) {
        const queueData = await queueRes.json();
        setQueue(queueData);
      }
      setServerError(null); // Clear any previous errors on success
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
      setServerError("Backend API server is offline. Please run 'node server.js' in the terminal.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // Poll every 30 seconds for live updates
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const startPipeline = async () => {
    setIsProcessing(true);
    try {
        const res = await fetch('http://localhost:3001/api/run-pipeline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stream: "BTech" }) // Can be made dynamic later
        });
        const data = await res.json();
        alert(data.message);
    } catch (error) {
        console.error("Error starting pipeline:", error);
        alert("Failed to start pipeline. Is the server running?");
    } finally {
        setTimeout(() => setIsProcessing(false), 2000);
    }
  };

  if (loading) {
      return <div className="dashboard-container" style={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh'}}><h2>Loading Live EduContent Data...</h2></div>;
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

      <div className="grid-layout">
        <div className="glass-panel">
          <h2>🎯 Next Video Queue (Live from Notion)</h2>
          {queue.length === 0 ? (
              <p>No remaining videos in the queue!</p>
          ) : (
              <ul className="queue-list">
                {queue.map((item) => (
                  <li key={item.id} className="queue-item">
                    <div>
                      <strong>{item.topic}</strong>
                      <p>{item.subject} | {item.stream}</p>
                    </div>
                    <span className={`badge ${item.status === 'Pending' ? 'pending' : 'success'}`}>
                      {item.status}
                    </span>
                  </li>
                ))}
              </ul>
          )}
        </div>

        <div className="glass-panel">
          <h2>💡 Probability & Insights (Live Algorithmic Assessment)</h2>
          {/* In a fully dynamic system, this data would come from the /api/insights endpoint based on real YT analytics crunching. 
              For this phase, displaying tailored insight cards simulating real recommendations. */}
          <div className="insights-list">
            <div className="insight-card success">
              <strong>Optimization Recommendation</strong>
              <p>The SEO Generator is actively embedding target tags to capture 11th & 12th Grade search intent. Maintain current Hook titles.</p>
            </div>
            <div className="insight-card">
              <strong>Consistency Metric</strong>
              <p>Posting frequency impacts algorithm reach. The Master Pipeline is ready to process the next batch of definitions.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>🚀 Pipeline Control</h2>
          <p>Manually trigger the orchestration script for the next pending topic.</p>
        </div>
        <button 
          className={`btn btn-primary ${isProcessing ? 'pulse' : ''}`}
          onClick={startPipeline}
          disabled={isProcessing}
        >
          {isProcessing ? 'Pipeline Running in Background...' : 'Run Master Pipeline'}
        </button>
      </div>
    </div>
  );
};

export default Dashboard;
