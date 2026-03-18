import React from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Calendar, TrendingUp, Users, Clock } from 'lucide-react';

// Mocked analytics data
const performanceData = [
  { name: 'Jan', views: 4000, watchTime: 2400 },
  { name: 'Feb', views: 3000, watchTime: 1398 },
  { name: 'Mar', views: 2000, watchTime: 9800 },
  { name: 'Apr', views: 2780, watchTime: 3908 },
  { name: 'May', views: 1890, watchTime: 4800 },
  { name: 'Jun', views: 2390, watchTime: 3800 },
  { name: 'Jul', views: 3490, watchTime: 4300 },
];

const bestTimeData = [
  { time: '6 AM', engagement: 20 },
  { time: '9 AM', engagement: 45 },
  { time: '12 PM', engagement: 30 },
  { time: '3 PM', engagement: 65 },
  { time: '6 PM', engagement: 100 },
  { time: '9 PM', engagement: 85 },
];

const Analytics = () => {
    return (
        <div className="dashboard-container" style={{ paddingTop: '0' }}>
            <h1>Analytics & Performance</h1>
            
            {/* Quick Stats Row */}
            <div className="grid-layout" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))' }}>
                <div className="glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1.5rem' }}>
                    <div style={{ padding: '1rem', background: 'rgba(59, 130, 246, 0.2)', borderRadius: '12px', color: '#3b82f6' }}>
                        <Users size={24} />
                    </div>
                    <div>
                        <p style={{ margin: 0, fontSize: '0.85rem', textTransform: 'uppercase' }}>Audience Growth</p>
                        <h3 style={{ margin: 0, fontSize: '1.5rem' }}>+1,204</h3>
                    </div>
                </div>
                <div className="glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1.5rem' }}>
                    <div style={{ padding: '1rem', background: 'rgba(16, 185, 129, 0.2)', borderRadius: '12px', color: '#10b981' }}>
                        <TrendingUp size={24} />
                    </div>
                    <div>
                        <p style={{ margin: 0, fontSize: '0.85rem', textTransform: 'uppercase' }}>Avg. View Duration</p>
                        <h3 style={{ margin: 0, fontSize: '1.5rem' }}>4m 12s</h3>
                    </div>
                </div>
                <div className="glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1.5rem' }}>
                    <div style={{ padding: '1rem', background: 'rgba(245, 158, 11, 0.2)', borderRadius: '12px', color: '#f59e0b' }}>
                        <Clock size={24} />
                    </div>
                    <div>
                        <p style={{ margin: 0, fontSize: '0.85rem', textTransform: 'uppercase' }}>Upload Frequency</p>
                        <h3 style={{ margin: 0, fontSize: '1.5rem' }}>2.4 / week</h3>
                    </div>
                </div>
            </div>

            <div className="grid-layout" style={{ gridTemplateColumns: '2fr 1fr' }}>
                {/* Main Graph */}
                <div className="glass-panel">
                    <h2>View Velocity & Retension</h2>
                    <p style={{ marginBottom: '1.5rem' }}>Comparing total views vs watch time over the last 7 months.</p>
                    <div style={{ width: '100%', height: 300 }}>
                        <ResponsiveContainer>
                            <AreaChart data={performanceData}>
                                <defs>
                                    <linearGradient id="colorViews" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                                <XAxis dataKey="name" stroke="#94a3b8" />
                                <YAxis stroke="#94a3b8" />
                                <Tooltip 
                                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                                    itemStyle={{ color: '#f8fafc' }}
                                />
                                <Area type="monotone" dataKey="views" stroke="#3b82f6" fillOpacity={1} fill="url(#colorViews)" />
                                <Line type="monotone" dataKey="watchTime" stroke="#10b981" strokeWidth={2} dot={false} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Best Time to Post */}
                <div className="glass-panel">
                    <h2>Best Time to Post</h2>
                    <p style={{ marginBottom: '1.5rem' }}>Based on subscriber activity metrics.</p>
                    <div style={{ width: '100%', height: 250 }}>
                        <ResponsiveContainer>
                            <BarChart data={bestTimeData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                                <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} />
                                <Tooltip 
                                    cursor={{fill: 'rgba(255,255,255,0.05)'}}
                                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                                />
                                <Bar dataKey="engagement" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                    <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(139, 92, 246, 0.1)', borderRadius: '8px', borderLeft: '4px solid #8b5cf6' }}>
                        <strong style={{ display: 'block', color: '#c4b5fd', marginBottom: '4px' }}>Recommendation:</strong>
                        <span style={{ fontSize: '0.85rem' }}>Schedule your next upload for <strong>6 PM</strong> to maximize initial algorithmic push.</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Analytics;
