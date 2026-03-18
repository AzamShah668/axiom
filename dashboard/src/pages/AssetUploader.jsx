import React, { useState, useRef } from 'react';
import { UploadCloud, FileAudio, FileText, CheckCircle, AlertCircle } from 'lucide-react';

const AssetUploader = () => {
    const [dragActive, setDragActive] = useState(false);
    const [files, setFiles] = useState([]);
    const [uploadStatus, setUploadStatus] = useState('idle'); // idle, uploading, success, error
    const inputRef = useRef(null);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFiles(e.dataTransfer.files);
        }
    };

    const handleChange = (e) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            handleFiles(e.target.files);
        }
    };

    const handleFiles = (newFiles) => {
        const fileArray = Array.from(newFiles);
        // Only accept wav, txt, json
        const validFiles = fileArray.filter(f => f.name.endsWith('.wav') || f.name.endsWith('.txt') || f.name.endsWith('.json'));
        setFiles(prev => [...prev, ...validFiles]);
    };

    const removeFile = (index) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleUploadClick = () => {
        inputRef.current.click();
    };

    const submitFiles = async () => {
        if (files.length === 0) return;
        setUploadStatus('uploading');

        const formData = new FormData();
        files.forEach(file => {
            formData.append('assets', file);
        });

        try {
            const response = await fetch('http://localhost:3001/api/upload', {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                setUploadStatus('success');
                setTimeout(() => {
                    setFiles([]);
                    setUploadStatus('idle');
                }, 3000);
            } else {
                setUploadStatus('error');
            }
        } catch (error) {
            console.error(error);
            setUploadStatus('error');
        }
    };

    const getFileIcon = (filename) => {
        if (filename.endsWith('.wav')) return <FileAudio size={24} color="#8b5cf6" />;
        if (filename.endsWith('.txt')) return <FileText size={24} color="#3b82f6" />;
        if (filename.endsWith('.json')) return <FileText size={24} color="#10b981" />;
        return <FileText size={24} color="#94a3b8" />;
    };

    return (
        <div className="dashboard-container" style={{ paddingTop: '0', maxWidth: '800px' }}>
            <h1>Asset Uploader</h1>
            <p style={{ marginBottom: '2rem' }}>Drop your exported NotebookLM files (`.wav` audio, `.txt` transcript, `.json` timeline) here. They will be automatically routed to the inner pipeline data folder.</p>
            
            <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
                <div 
                    className={`upload-zone ${dragActive ? 'drag-active' : ''}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    onClick={handleUploadClick}
                    style={{
                        padding: '4rem 2rem', border: dragActive ? '2px dashed #3b82f6' : '2px dashed rgba(255,255,255,0.2)',
                        background: dragActive ? 'rgba(59, 130, 246, 0.05)' : 'transparent',
                        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                        cursor: 'pointer', transition: 'all 0.3s ease', minHeight: '300px'
                    }}
                >
                    <input 
                        ref={inputRef} 
                        type="file" 
                        multiple 
                        accept=".wav,.txt,.json" 
                        onChange={handleChange} 
                        style={{ display: 'none' }} 
                    />
                    
                    <UploadCloud size={64} color={dragActive ? '#3b82f6' : 'rgba(255,255,255,0.4)'} style={{ marginBottom: '1rem', transition: 'color 0.3s ease' }} />
                    <h3 style={{ margin: 0, color: dragActive ? '#3b82f6' : '#f8fafc' }}>Drag & drop files here</h3>
                    <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>or click to browse from your computer</p>
                </div>

                <div style={{ padding: '1.5rem', background: 'rgba(0,0,0,0.2)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Queued Files</h3>
                        <span className="badge" style={{ background: 'rgba(255,255,255,0.1)' }}>{files.length} selected</span>
                    </div>

                    {files.length === 0 ? (
                        <p style={{ fontSize: '0.85rem', fontStyle: 'italic', textAlign: 'center', margin: '2rem 0' }}>No files selected.</p>
                    ) : (
                        <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 1.5rem 0', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {files.map((file, idx) => (
                                <li key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                        {getFileIcon(file.name)}
                                        <span style={{ fontWeight: 500, fontSize: '0.95rem' }}>{file.name}</span>
                                    </div>
                                    <button onClick={() => removeFile(idx)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontWeight: 'bold' }}>✕</button>
                                </li>
                            ))}
                        </ul>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            {uploadStatus === 'success' && <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#10b981' }}><CheckCircle size={18} /> Upload Complete</div>}
                            {uploadStatus === 'error' && <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444' }}><AlertCircle size={18} /> Upload Failed</div>}
                        </div>
                        <button 
                            className={`btn btn-primary ${uploadStatus === 'uploading' ? 'pulse' : ''}`}
                            onClick={submitFiles}
                            disabled={files.length === 0 || uploadStatus === 'uploading'}
                        >
                            {uploadStatus === 'uploading' ? 'Publishing to /data...' : 'Upload Assets'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AssetUploader;
