import React, { useState, useEffect } from 'react';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import StatusBadge from '../components/StatusBadge';
import { History, Filter, AlertCircle, RefreshCw } from 'lucide-react';

export default function AdminLogs() {
  const [logs, setLogs] = useState([]);
  const [outcomeFilter, setOutcomeFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadLogs = async () => {
    try {
      setLoading(true);
      setError('');
      const params = outcomeFilter ? { outcome: outcomeFilter } : {};
      const res = await api.get('/admin/logs', { params });
      setLogs(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch audit activity logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [outcomeFilter]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Breadcrumbs items={[{ to: '/admin', label: 'Admin' }, { label: 'Audit Logs' }]} />
        <button
          onClick={loadLogs}
          data-testid="refresh-logs-btn"
          className="px-3.5 py-1.5 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-xs"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-extrabold text-slate-900">Research Authorization Telemetry</h1>
        <p className="text-sm text-slate-500 mt-1">
          Detailed security logs evaluating Small Language Model browser-agent policy compliance.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Filter toolbar */}
      <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Filter size={16} className="text-slate-400" />
          <span className="text-xs font-semibold text-slate-600 uppercase">Outcome Filter:</span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setOutcomeFilter('')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                outcomeFilter === '' ? 'bg-navy-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              All Events ({logs.length})
            </button>
            <button
              onClick={() => setOutcomeFilter('ALLOW')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                outcomeFilter === 'ALLOW' ? 'bg-emerald-700 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Allowed (200/201)
            </button>
            <button
              onClick={() => setOutcomeFilter('BLOCK')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                outcomeFilter === 'BLOCK' ? 'bg-rose-700 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Blocked (403/401)
            </button>
          </div>
        </div>
        <span className="text-xs text-slate-400 font-mono">Backend Enforced Guardrails</span>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600" data-testid="audit-logs-table">
            <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3.5 px-6">Timestamp</th>
                <th className="py-3.5 px-6">User Persona</th>
                <th className="py-3.5 px-6">Action</th>
                <th className="py-3.5 px-6">Target Resource</th>
                <th className="py-3.5 px-6">Decision</th>
                <th className="py-3.5 px-6">Reason / Diagnostics</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-xs">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50/50 transition-colors" data-testid={`log-row-${log.id}`}>
                  <td className="py-3.5 px-6 text-slate-400 whitespace-nowrap">
                    {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '—'}
                  </td>
                  <td className="py-3.5 px-6 font-bold text-slate-900 font-sans">
                    {log.username} <span className="text-slate-400 font-normal">({log.role})</span>
                  </td>
                  <td className="py-3.5 px-6 text-slate-800 font-bold">
                    {log.action}
                  </td>
                  <td className="py-3.5 px-6 text-slate-600">
                    {log.resource_type}:{log.resource_id || '*'}
                  </td>
                  <td className="py-3.5 px-6 font-sans">
                    <StatusBadge status={log.outcome} />
                  </td>
                  <td className="py-3.5 px-6 text-slate-600 max-w-md font-sans text-xs">
                    {log.detail}
                  </td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr>
                  <td colSpan="6" className="py-12 text-center text-slate-400 font-sans text-xs italic">
                    No activity logs recorded matching selected criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
