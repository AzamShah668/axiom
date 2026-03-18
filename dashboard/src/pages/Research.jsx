import React, { useState } from 'react';
import { Search, TrendingUp, Youtube, ExternalLink } from 'lucide-react';

const mockCompetitorData = [
  { id: 1, channel: "Physics Wallah", title: "Newton's Laws Complete Revision in 1 Shot", views: "1.2M", published: "2 days ago", tag: "High Velocity" },
  { id: 2, channel: "Aman Dhattarwal", title: "How to master Biology for NEET/Boards", views: "850K", published: "1 week ago", tag: "Evergreen" },
  { id: 3, channel: "Unacademy JEE", title: "Integration Tricks - Solve in 10s", views: "420K", published: "12 hours ago", tag: "Trending" },
];

const mockTrendingTopics = [
  { topic: "Quantum Biology", score: 98, searchVolume: "High", difficulty: "Medium" },
  { topic: "CBSE Exam Dates 2026", score: 95, searchVolume: "Very High", difficulty: "Low" },
  { topic: "Organic Chemistry Nomenclature", score: 87, searchVolume: "Medium", difficulty: "High" },
  { topic: "Vectors 3D Animation", score: 82, searchVolume: "High", difficulty: "Medium" },
];

const Research = () => {
    const [searchQuery, setSearchQuery] = useState("");

    return (
        <div className="dashboard-container" style={{ paddingTop: '0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h1>Research & Trending</h1>
                <div style={{ position: 'relative', width: '300px' }}>
                    <Search className="search-icon" size={18} style={{ position: 'absolute', left: '12px', top: '12px', color: '#94a3b8' }} />
                    <input 
                        type="text" 
                        placeholder="Analyze topic..." 
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{ 
                            width: '100%', padding: '10px 10px 10px 40px', 
                            borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', 
                            background: 'rgba(0,0,0,0.2)', color: 'white', outline: 'none' 
                        }}
                    />
                </div>
            </div>

            <div className="grid-layout" style={{ gridTemplateColumns: '1fr 1fr' }}>
                
                {/* Competitor Analysis */}
                <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <h2><Youtube size={24} color="#ef4444" /> Competitor Intel</h2>
                    <p style={{ margin: 0 }}>Recent high-performing videos in your niche.</p>
                    
                    <div className="queue-list" style={{ marginTop: '1rem' }}>
                        {mockCompetitorData.map(item => (
                            <div key={item.id} className="queue-item" style={{ alignItems: 'flex-start' }}>
                                <div style={{ flex: 1 }}>
                                    <strong style={{ display: 'block', fontSize: '1rem', marginBottom: '4px' }}>{item.title}</strong>
                                    <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem', color: '#94a3b8' }}>
                                        <span>{item.channel}</span>
                                        <span>•</span>
                                        <span>{item.views} views</span>
                                        <span>•</span>
                                        <span>{item.published}</span>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                                    <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa' }}>{item.tag}</span>
                                    <a href="#" style={{ color: '#94a3b8', hover: '#fff' }}><ExternalLink size={16} /></a>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Trending Topics Algorithm */}
                <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <h2><TrendingUp size={24} color="#10b981" /> Opportunity Map</h2>
                    <p style={{ margin: 0 }}>Topics predicted to over-perform based on search volume vs. supply.</p>

                    <div style={{ marginTop: '1rem' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8' }}>
                                    <th style={{ padding: '12px 8px', fontWeight: 500 }}>Topic</th>
                                    <th style={{ padding: '12px 8px', fontWeight: 500 }}>Opportunity Score</th>
                                    <th style={{ padding: '12px 8px', fontWeight: 500 }}>Search Vol</th>
                                    <th style={{ padding: '12px 8px', fontWeight: 500 }}>Competition</th>
                                </tr>
                            </thead>
                            <tbody>
                                {mockTrendingTopics.map((item, index) => (
                                    <tr key={index} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                        <td style={{ padding: '16px 8px', fontWeight: 'bold' }}>{item.topic}</td>
                                        <td style={{ padding: '16px 8px' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                                                    <div style={{ height: '100%', width: `${item.score}%`, background: item.score > 90 ? '#10b981' : '#3b82f6' }}></div>
                                                </div>
                                                <span style={{ fontSize: '0.85rem', color: item.score > 90 ? '#10b981' : '#3b82f6' }}>{item.score}</span>
                                            </div>
                                        </td>
                                        <td style={{ padding: '16px 8px', fontSize: '0.9rem' }}>{item.searchVolume}</td>
                                        <td style={{ padding: '16px 8px', fontSize: '0.9rem' }}>{item.difficulty}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Research;
