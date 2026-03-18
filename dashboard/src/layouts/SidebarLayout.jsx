import React from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { LayoutDashboard, BarChart2, Search, Upload } from 'lucide-react';

const SidebarLayout = () => {
  return (
    <div className="app-container">
      <nav className="sidebar glass-panel">
        <div className="sidebar-header">
          <h2>EduContent</h2>
          <p>Command Center</p>
        </div>
        <ul className="sidebar-menu">
          <li>
            <NavLink to="/" className={({ isActive }) => (isActive ? 'active-link' : '')}>
              <LayoutDashboard size={20} />
              <span>Overview</span>
            </NavLink>
          </li>
          <li>
            <NavLink to="/analytics" className={({ isActive }) => (isActive ? 'active-link' : '')}>
              <BarChart2 size={20} />
              <span>Analytics</span>
            </NavLink>
          </li>
          <li>
            <NavLink to="/research" className={({ isActive }) => (isActive ? 'active-link' : '')}>
              <Search size={20} />
              <span>Research</span>
            </NavLink>
          </li>
          <li>
            <NavLink to="/upload" className={({ isActive }) => (isActive ? 'active-link' : '')}>
              <Upload size={20} />
              <span>Asset Uploader</span>
            </NavLink>
          </li>
        </ul>
      </nav>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};

export default SidebarLayout;
