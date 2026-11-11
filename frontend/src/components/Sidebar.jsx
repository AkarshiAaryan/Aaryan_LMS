import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  BookOpen,
  ClipboardList,
  FileCheck2,
  Award,
  FolderOpen,
  Users,
  ShieldAlert,
  GraduationCap,
  Settings,
  History,
  Layers,
} from 'lucide-react';

export default function Sidebar() {
  const { user, isAdmin } = useAuth();

  const navClass = ({ isActive }) =>
    `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
      isActive
        ? 'bg-navy-800 text-white shadow-sm font-semibold'
        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
    }`;

  return (
    <aside
      className="w-64 bg-white border-r border-slate-200 fixed top-16 bottom-0 left-0 overflow-y-auto p-4 flex flex-col justify-between z-20"
      aria-label="Main Navigation"
    >
      <div className="space-y-6">
        {/* Core Learning Navigation */}
        <div>
          <p className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
            Academic Portal
          </p>
          <nav className="space-y-1">
            <NavLink to="/dashboard" className={navClass} data-testid="nav-dashboard">
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </NavLink>
            <NavLink to="/courses" className={navClass} data-testid="nav-courses">
              <BookOpen size={18} />
              <span>My Courses</span>
            </NavLink>
            <NavLink to="/assignments" className={navClass} data-testid="nav-assignments">
              <ClipboardList size={18} />
              <span>Assignments</span>
            </NavLink>
            <NavLink to="/quizzes" className={navClass} data-testid="nav-quizzes">
              <FileCheck2 size={18} />
              <span>Quizzes</span>
            </NavLink>
            <NavLink to="/grades" className={navClass} data-testid="nav-grades">
              <Award size={18} />
              <span>Gradebook</span>
            </NavLink>
            <NavLink to="/resources" className={navClass} data-testid="nav-resources">
              <FolderOpen size={18} />
              <span>Resources</span>
            </NavLink>
            {isAdmin && (
              <NavLink to="/directory" className={navClass} data-testid="nav-directory">
                <Users size={18} />
                <span>User Directory</span>
              </NavLink>
            )}
          </nav>
        </div>

        {/* Administration Section (Only visible to admin) */}
        {isAdmin && (
          <div>
            <p className="px-3 text-[11px] font-bold text-red-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <ShieldAlert size={12} />
              <span>Site Administration</span>
            </p>
            <nav className="space-y-1">
              <NavLink to="/admin" end className={navClass} data-testid="nav-admin-dashboard">
                <Settings size={18} />
                <span>Admin Console</span>
              </NavLink>
              <NavLink to="/admin/users" className={navClass} data-testid="nav-admin-users">
                <Users size={18} />
                <span>User Management</span>
              </NavLink>
              <NavLink to="/admin/enrolments" className={navClass} data-testid="nav-admin-enrolments">
                <Layers size={18} />
                <span>Enrolments</span>
              </NavLink>
              <NavLink to="/admin/logs" className={navClass} data-testid="nav-admin-logs">
                <History size={18} />
                <span>Audit Logs</span>
              </NavLink>
            </nav>
          </div>
        )}
      </div>

      {/* Footer Info Box */}
      <div className="pt-4 border-t border-slate-200">
        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-500">
          <p className="font-semibold text-slate-700">GuardSLM Benchmark</p>
          <p className="mt-0.5">Role: <span className="font-mono text-navy-800 capitalize font-medium">{user?.role}</span></p>
          <p className="text-[10px] text-slate-400 mt-1">Backend Enforced v1.0.0</p>
        </div>
      </div>
    </aside>
  );
}
