import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { GraduationCap, LogOut, User as UserIcon, Bell, Search, Shield, BookOpen } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Navbar() {
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const getRoleBadge = (role) => {
    switch (role) {
      case 'admin':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200" data-testid="role-badge"><Shield size={12}/> Admin</span>;
      case 'professor':
      case 'teacher':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 border border-indigo-200" data-testid="role-badge"><BookOpen size={12}/> Professor</span>;
      case 'ta':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200" data-testid="role-badge"><Shield size={12}/> TA</span>;
      case 'student':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200" data-testid="role-badge"><GraduationCap size={12}/> Student</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">{role}</span>;
    }
  };

  const getInitials = (name) => {
    if (!name) return 'U';
    return name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
  };

  return (
    <header className="bg-white border-b border-slate-200 h-16 fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-6 shadow-sm">
      {/* Brand logo & portal name */}
      <div className="flex items-center gap-3">
        <Link to="/dashboard" className="flex items-center gap-2.5 group">
          <div className="w-10 h-10 rounded-lg bg-navy-800 text-white flex items-center justify-center shadow group-hover:bg-navy-900 transition-colors">
            <GraduationCap size={22} />
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-lg leading-tight tracking-tight text-navy-900">GuardSLM</span>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Research LMS</span>
          </div>
        </Link>
      </div>

      {/* Global search input */}
      <div className="hidden md:flex items-center max-w-md w-full mx-8">
        <div className="relative w-full">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search courses, assignments, or records..."
            data-testid="global-search-input"
            className="w-full pl-9 pr-4 py-1.5 text-sm bg-slate-100 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all text-slate-700"
          />
        </div>
      </div>

      {/* User profile controls & Role indicator */}
      <div className="flex items-center gap-4">
        {/* Research Environment Tag */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-100 text-slate-600 text-xs font-medium border border-slate-200">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span>Environment: Isolated Testbed</span>
        </div>

        {/* Notifications Icon */}
        <button
          className="relative p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          title="Notifications"
          data-testid="notifications-button"
        >
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-600 rounded-full"></span>
        </button>

        {/* User Role Badge */}
        {user && getRoleBadge(user.role)}

        {/* Profile Dropdown */}
        {user && (
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2.5 p-1 rounded-lg hover:bg-slate-100 transition-colors"
              data-testid="user-profile-menu-button"
              aria-label="User profile menu"
            >
              <div className="w-9 h-9 rounded-full bg-indigo-600 text-white flex items-center justify-center font-semibold text-sm shadow-sm">
                {getInitials(user.full_name)}
              </div>
              <div className="hidden md:flex flex-col text-left">
                <span className="text-sm font-semibold text-slate-800 leading-tight" data-testid="user-full-name">{user.full_name}</span>
                <span className="text-xs text-slate-500 font-mono">@{user.username}</span>
              </div>
            </button>

            {dropdownOpen && (
              <div
                className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-lg border border-slate-200 py-1.5 z-50 animate-in fade-in slide-in-from-top-2 duration-150"
                data-testid="user-profile-dropdown"
              >
                <div className="px-4 py-2.5 border-b border-slate-100">
                  <p className="text-xs text-slate-500 font-medium">Signed in as</p>
                  <p className="text-sm font-bold text-slate-800 truncate">{user.email || user.username}</p>
                  <p className="text-xs text-slate-500 capitalize mt-0.5">Role: <span className="font-semibold text-navy-800">{user.role}</span></p>
                </div>

                <div className="py-1">
                  <div className="px-4 py-1.5 text-xs text-slate-500 font-medium">
                    User ID: <span className="font-mono text-slate-700">{user.id}</span>
                  </div>
                </div>

                <div className="border-t border-slate-100 pt-1">
                  <button
                    onClick={() => { setDropdownOpen(false); logout(); }}
                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 font-medium transition-colors"
                    data-testid="logout-button"
                  >
                    <LogOut size={16} />
                    <span>Sign out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
