import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import StatCard from '../components/StatCard';
import { Users, BookOpen, Layers, History, ShieldAlert, ArrowRight, Settings } from 'lucide-react';

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const res = await api.get('/admin/stats');
        setStats(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Administrator access required.');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 bg-white border border-red-200 rounded-2xl shadow-sm text-center max-w-lg mx-auto">
        <ShieldAlert size={36} className="text-red-600 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-slate-900 mb-2">Access Denied</h2>
        <p className="text-sm text-slate-600 mb-4">{error}</p>
        <Link to="/dashboard" className="px-4 py-2 bg-navy-800 text-white rounded-lg text-xs font-semibold">
          Return to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-console-page">
      <Breadcrumbs items={[{ label: 'Site Administration' }]} />

      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-extrabold text-slate-900">Administration Console</h1>
        <p className="text-sm text-slate-500 mt-1">
          Full institutional control over users, course enrolments, and policy enforcement logs.
        </p>
      </div>

      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <StatCard
            title="Total Users"
            value={stats.total_users}
            subtitle={`${stats.total_students} Students · ${stats.total_teachers} Teachers`}
            icon={Users}
            color="blue"
          />
          <StatCard
            title="Courses"
            value={stats.total_courses}
            subtitle={`${stats.total_enrollments} Total Enrolments`}
            icon={BookOpen}
            color="indigo"
          />
          <StatCard
            title="Submissions"
            value={stats.total_submissions}
            subtitle="Assignment records"
            icon={Layers}
            color="emerald"
          />
          <StatCard
            title="Telemetry Logs"
            value={stats.recent_activity_count}
            subtitle="Research audit events"
            icon={History}
            color="rose"
          />
        </div>
      )}

      {/* Admin Modules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center mb-4">
              <Users size={24} />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-1">User Management</h3>
            <p className="text-xs text-slate-500 mb-6">
              Create new student or faculty accounts, change user roles, and activate or deactivate logins.
            </p>
          </div>
          <Link
            to="/admin/users"
            data-testid="admin-users-card-link"
            className="px-4 py-2.5 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center justify-between transition-colors shadow-sm"
          >
            <span>Manage Users</span>
            <ArrowRight size={14} />
          </Link>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center mb-4">
              <Layers size={24} />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-1">Course Enrolments</h3>
            <p className="text-xs text-slate-500 mb-6">
              Enrol or remove students across courses. Enforce multi-tenant course boundaries.
            </p>
          </div>
          <Link
            to="/admin/enrolments"
            data-testid="admin-enrolments-card-link"
            className="px-4 py-2.5 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center justify-between transition-colors shadow-sm"
          >
            <span>Manage Enrolments</span>
            <ArrowRight size={14} />
          </Link>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-700 flex items-center justify-center mb-4">
              <History size={24} />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-1">Audit Telemetry</h3>
            <p className="text-xs text-slate-500 mb-6">
              Review real-time ALLOW/BLOCK authorization decisions for Small Language Model agent testing.
            </p>
          </div>
          <Link
            to="/admin/logs"
            data-testid="admin-logs-card-link"
            className="px-4 py-2.5 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center justify-between transition-colors shadow-sm"
          >
            <span>Inspect Audit Logs</span>
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </div>
  );
}
