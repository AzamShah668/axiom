import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import SidebarLayout from './layouts/SidebarLayout';
import Dashboard from './pages/Dashboard';
import Analytics from './pages/Analytics';
import Research from './pages/Research';
import AssetUploader from './pages/AssetUploader';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<SidebarLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="research" element={<Research />} />
          <Route path="upload" element={<AssetUploader />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
