import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { TrendingUp, Users, Clock, Video } from 'lucide-react';

const Analytics = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('http://localhost:3001/api/analytics/youtube')
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  if (loading) return (
    <div className="dashboard-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
      <h2>Loading analytics...</h2>
    </div>
  );

  // Derived values
  const videos      = data?.videos || [];
  const hourlyIST   = data?.hourlyIST || [];
  const bestHour    = data?.bestHourIST ?? 18;
  const totalVideos = data?.totalVideos || 0;

  const totalViews = videos.reduce((s, v) => s + v.views, 0);
  const totalLikes = videos.reduce((s, v) => s + v.likes, 0);

  // Last 12 videos for the area chart (oldest → newest)
  const recentVideos = [...videos].reverse().slice(0, 12).map((v, i) => ({
    name:  `V${i + 1}`,
    views: v.views,
    likes: v.likes,
    title: v.title,
  }));

  // Only show hours with at least 1 upload in the bar chart
  const hourChart = hourlyIST
    .filter(h => h.count > 0 || h.hour === bestHour)
    .map(h => ({
      ...h,
      avgViews: h.count > 0 ? Math.round(h.views / h.count) : 0,
      fill: h.hour === bestHour ? '#10b981' : '#8b5cf6',
    }));

  const bestLabel = bestHour === 0 ? '12 AM' : bestHour < 12 ? `${bestHour} AM` : bestHour === 12 ? '12 PM' : `${bestHour - 12} PM`;
  const hasEnoughData = videos.length >= 3;

  return (
    <div className="dashboard-container" style={{ paddingTop: 0 }}>
      <h1>Analytics & Performance</h1>

      {error && (
        <div className="glass-panel" style={{ borderLeft: '4px solid var(--warning)', marginBottom: '1rem' }}>
          <p style={{ margin: 0, color: '#f59e0b' }}>Could not load YouTube data: {error}</p>
        </div>
      )}

      {/* ── Quick Stats ─────────────────────────────────── */}
      <div className="grid-layout" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        {[
          { icon: <Video size={22} />, label: 'Videos Uploaded', value: totalVideos, color: '#3b82f6' },
          { icon: <Users size={22} />, label: 'Total Views', value: totalViews.toLocaleString(), color: '#10b981' },
          { icon: <TrendingUp size={22} />, label: 'Total Likes', value: totalLikes.toLocaleString(), color: '#f59e0b' },
          { icon: <Clock size={22} />, label: 'Best Upload Time', value: `${bestLabel} IST`, color: '#8b5cf6' },
        ].map(s => (
          <div key={s.label} className="glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1.5rem' }}>
            <div style={{ padding: '0.9rem', background: `${s.color}22`, borderRadius: '12px', color: s.color }}>
              {s.icon}
            </div>
            <div>
              <p style={{ margin: 0, fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8' }}>{s.label}</p>
              <h3 style={{ margin: 0, fontSize: '1.4rem' }}>{s.value}</h3>
            </div>
          </div>
        ))}
      </div>

      <div className="grid-layout" style={{ gridTemplateColumns: '2fr 1fr' }}>
        {/* ── View History ────────────────────────────── */}
        <div className="glass-panel">
          <h2>View History (Last {recentVideos.length} Videos)</h2>
          {recentVideos.length === 0 ? (
            <p style={{ color: '#64748b' }}>No video data yet. Upload your first video to see performance here.</p>
          ) : (
            <div style={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <AreaChart data={recentVideos}>
                  <defs>
                    <linearGradient id="gViews" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    formatter={(val, name, props) => [val.toLocaleString(), name === 'views' ? 'Views' : 'Likes']}
                    labelFormatter={(_, payload) => payload?.[0]?.payload?.title || ''}
                  />
                  <Area type="monotone" dataKey="views" stroke="#3b82f6" fillOpacity={1} fill="url(#gViews)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* ── Best Time to Post ───────────────────────── */}
        <div className="glass-panel">
          <h2>Best Time to Post</h2>
          <p style={{ marginBottom: '1.2rem', color: '#94a3b8', fontSize: '0.85rem' }}>
            {hasEnoughData
              ? 'Based on avg views by upload hour (IST) from your channel history.'
              : 'Not enough data yet — showing recommended default for Indian student content.'}
          </p>

          {hourChart.length > 0 ? (
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={hourChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" vertical={false} />
                  <XAxis dataKey="label" stroke="#94a3b8" fontSize={11} />
                  <Tooltip
                    cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                    formatter={v => [v.toLocaleString(), 'Avg Views']}
                  />
                  <Bar dataKey="avgViews" radius={[4, 4, 0, 0]}
                    fill="#8b5cf6"
                    label={false}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            // No uploads yet — show static recommended hours
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={[
                  { label: '9 AM', avgViews: 45 }, { label: '12 PM', avgViews: 30 },
                  { label: '3 PM', avgViews: 65 }, { label: '6 PM', avgViews: 100 },
                  { label: '9 PM', avgViews: 80 },
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" vertical={false} />
                  <XAxis dataKey="label" stroke="#94a3b8" fontSize={11} />
                  <Tooltip cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                    formatter={v => [`${v}%`, 'Rel. Engagement']} />
                  <Bar dataKey="avgViews" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div style={{ marginTop: '1rem', padding: '0.9rem 1rem', background: 'rgba(139,92,246,0.12)', borderRadius: '8px', borderLeft: '4px solid #8b5cf6' }}>
            <strong style={{ display: 'block', color: '#c4b5fd', marginBottom: '4px' }}>
              {hasEnoughData ? 'Data-Driven Pick' : 'Recommended Default'}
            </strong>
            <span style={{ fontSize: '0.85rem' }}>
              Schedule uploads for <strong>{bestLabel} IST</strong> to maximise initial algorithmic push.
              {!hasEnoughData && ' (Based on Indian student viewing patterns — will update as your channel grows.)'}
            </span>
          </div>
        </div>
      </div>

      {/* ── Recent Videos Table ─────────────────────── */}
      {videos.length > 0 && (
        <div className="glass-panel">
          <h2>Recent Videos</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8', textAlign: 'left' }}>
                <th style={{ padding: '8px 12px' }}>Title</th>
                <th style={{ padding: '8px 12px' }}>Published</th>
                <th style={{ padding: '8px 12px' }}>Views</th>
                <th style={{ padding: '8px 12px' }}>Likes</th>
              </tr>
            </thead>
            <tbody>
              {videos.slice(0, 10).map((v, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px 12px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.title}</td>
                  <td style={{ padding: '10px 12px', color: '#94a3b8' }}>{new Date(v.publishedAt).toLocaleDateString('en-IN')}</td>
                  <td style={{ padding: '10px 12px' }}>{v.views.toLocaleString()}</td>
                  <td style={{ padding: '10px 12px' }}>{v.likes.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default Analytics;
