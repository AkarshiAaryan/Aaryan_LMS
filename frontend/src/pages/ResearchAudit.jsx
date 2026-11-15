import React, { useState, useEffect } from 'react';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Play,
  Download,
  FileJson,
  FileSpreadsheet,
  CheckCircle2,
  XCircle,
  Clock,
  Filter,
  BarChart3,
  Sliders,
  History,
  Bot,
  RefreshCw,
  Search,
  Check,
  Upload,
} from 'lucide-react';

export default function ResearchAudit() {
  const { user, isAdmin } = useAuth();

  const [activeTab, setActiveTab] = useState('timeline');
  const [conversations, setConversations] = useState([]);
  const [selectedConvId, setSelectedConvId] = useState(null);
  const [selectedConvDetail, setSelectedConvDetail] = useState(null);
  const [auditReport, setAuditReport] = useState(null);

  // Scenarios state
  const [scenarios, setScenarios] = useState([]);
  const [scenarioFilter, setScenarioFilter] = useState('all');
  const [scenarioResults, setScenarioResults] = useState({});
  const [runningScenarios, setRunningScenarios] = useState(false);
  const [runningSingle, setRunningSingle] = useState(null);

  // Policies state
  const [policies, setPolicies] = useState([]);
  const [policyRoleFilter, setPolicyRoleFilter] = useState('all');

  // Loading & metrics
  const [loading, setLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [convRes, scenRes, polRes] = await Promise.all([
        api.get('/api/ai/conversations?all=true'),
        api.get('/api/ai/scenarios'),
        api.get('/api/ai/policies'),
      ]);
      setConversations(convRes.data);
      setScenarios(scenRes.data);
      setPolicies(polRes.data);

      if (convRes.data.length > 0) {
        selectConversation(convRes.data[0].conversation_id);
      }
    } catch (err) {
      console.error('Failed to load research audit data', err);
    } finally {
      setLoading(false);
    }
  };

  const selectConversation = async (convId) => {
    setSelectedConvId(convId);
    try {
      const [detailRes, auditRes] = await Promise.all([
        api.get(`/api/ai/conversations/${convId}`),
        api.get(`/api/ai/conversations/${convId}/audit`),
      ]);
      setSelectedConvDetail(detailRes.data);
      setAuditReport(auditRes.data);
    } catch (err) {
      console.error('Failed to load conversation details', err);
    }
  };

  const runSingleScenario = async (scenarioId) => {
    setRunningSingle(scenarioId);
    try {
      const res = await api.post('/api/ai/scenarios/run', { scenario_id: scenarioId });
      setScenarioResults((prev) => ({
        ...prev,
        [scenarioId]: res.data,
      }));
    } catch (err) {
      console.error(`Failed to run scenario ${scenarioId}`, err);
    } finally {
      setRunningSingle(null);
    }
  };

  const runAllScenarios = async () => {
    setRunningScenarios(true);
    const filtered = scenarios.filter(
      (s) => scenarioFilter === 'all' || s.category === scenarioFilter
    );

    for (const sc of filtered) {
      try {
        const res = await api.post('/api/ai/scenarios/run', { scenario_id: sc.id });
        setScenarioResults((prev) => ({
          ...prev,
          [sc.id]: res.data,
        }));
      } catch (err) {
        console.error(`Error running ${sc.id}`, err);
      }
    }
    setRunningScenarios(false);
  };

  const handleExportData = async (format) => {
    setExportLoading(true);
    try {
      const res = await api.get(`/api/ai/audit/export?format=${format}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `guardslm_ai_dataset.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Failed to export dataset', err);
    } finally {
      setExportLoading(false);
    }
  };

  // Metrics computation
  const totalInteractions = conversations.reduce((acc, c) => acc + (c.interaction_count || 0), 0);

  const filteredScenarios = scenarios.filter(
    (s) => scenarioFilter === 'all' || s.category === scenarioFilter
  );

  const scenarioPassCount = Object.values(scenarioResults).filter((r) => r.passed).length;
  const scenarioTotalRun = Object.keys(scenarioResults).length;

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Research & Compliance Console</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-navy-100 text-navy-800 border border-navy-200">
              Deterministic Testbed
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Authoritative Policy Guard telemetry, multi-turn conversation auditing, and 51 standard scenario benchmarks.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExportData('json')}
            disabled={exportLoading}
            className="flex items-center gap-2 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-xl border border-slate-300 shadow-sm transition"
          >
            <FileJson size={15} className="text-amber-600" />
            <span>Export JSON</span>
          </button>
          <button
            onClick={() => handleExportData('csv')}
            disabled={exportLoading}
            className="flex items-center gap-2 px-3.5 py-2 bg-navy-800 hover:bg-navy-900 text-white text-xs font-semibold rounded-xl shadow-sm transition"
          >
            <FileSpreadsheet size={15} className="text-emerald-400" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
            <History size={20} />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Total Sessions</p>
            <p className="text-xl font-bold text-slate-900">{conversations.length}</p>
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-purple-50 text-purple-600 rounded-lg">
            <Bot size={20} />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Logged Interactions</p>
            <p className="text-xl font-bold text-slate-900">{totalInteractions}</p>
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg">
            <ShieldCheck size={20} />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Standard Scenarios</p>
            <p className="text-xl font-bold text-slate-900">{scenarios.length} Defined</p>
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-amber-50 text-amber-600 rounded-lg">
            <CheckCircle2 size={20} />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Benchmark Accuracy</p>
            <p className="text-xl font-bold text-slate-900">
              {scenarioTotalRun > 0 ? `${Math.round((scenarioPassCount / scenarioTotalRun) * 100)}%` : '100%'}
              <span className="text-xs text-slate-400 font-normal ml-1">
                ({scenarioPassCount}/{scenarioTotalRun || scenarios.length})
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('timeline')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition ${
            activeTab === 'timeline'
              ? 'border-navy-800 text-navy-800'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <History size={16} />
          <span>Session Timeline & Auditor</span>
        </button>
        <button
          onClick={() => setActiveTab('scenarios')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition ${
            activeTab === 'scenarios'
              ? 'border-navy-800 text-navy-800'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Play size={16} />
          <span>Scenario Testbed (ST01-AU12)</span>
        </button>
        <button
          onClick={() => setActiveTab('policies')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition ${
            activeTab === 'policies'
              ? 'border-navy-800 text-navy-800'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sliders size={16} />
          <span>Active Policy Configuration</span>
        </button>
      </div>

      {/* TAB 1: Session Timeline & Auditor */}
      {activeTab === 'timeline' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Conversation List */}
          <div className="bg-white rounded-2xl border border-slate-200 p-4 space-y-3 shadow-sm h-fit max-h-[700px] overflow-y-auto">
            <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider">
              Recorded Sessions ({conversations.length})
            </h3>
            {conversations.length === 0 && (
              <p className="text-xs text-slate-500 italic p-4 text-center">No recorded AI sessions found.</p>
            )}
            <div className="space-y-1.5">
              {conversations.map((c) => (
                <button
                  key={c.conversation_id}
                  onClick={() => selectConversation(c.conversation_id)}
                  className={`w-full text-left p-3 rounded-xl border transition ${
                    selectedConvId === c.conversation_id
                      ? 'bg-navy-50/70 border-navy-800 text-navy-950 font-medium shadow-xs'
                      : 'bg-white border-slate-100 hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-bold text-slate-900 truncate max-w-[170px]">{c.title}</span>
                    <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                      {c.effective_role}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>{c.interaction_count} turns</span>
                    {c.latest_guard_decision && (
                      <span
                        className={`font-semibold ${
                          c.latest_guard_decision === 'ALLOW'
                            ? 'text-emerald-600'
                            : c.latest_guard_decision === 'LIMIT'
                            ? 'text-amber-600'
                            : 'text-rose-600'
                        }`}
                      >
                        {c.latest_guard_decision}
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Timeline and Auditor Assessment */}
          <div className="lg:col-span-2 space-y-6">
            {/* Auditor Assessment Card */}
            {auditReport && (
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-slate-900">Conversation Auditor Assessment</h3>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                        auditReport.audit_label === 'HARMLESS'
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                          : auditReport.audit_label === 'SUSPICIOUS'
                          ? 'bg-amber-100 text-amber-800 border border-amber-300'
                          : 'bg-rose-100 text-rose-800 border border-rose-300'
                      }`}
                    >
                      {auditReport.audit_label}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <span>Action:</span>
                    <span className="font-bold text-slate-800">{auditReport.recommended_action}</span>
                  </div>
                </div>

                <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-100">
                  {auditReport.explanation}
                </p>

                {auditReport.detected_patterns_json && JSON.parse(auditReport.detected_patterns_json).length > 0 && (
                  <div className="flex items-center gap-2 flex-wrap pt-1">
                    <span className="text-[11px] font-semibold text-slate-500">Detected Patterns:</span>
                    {JSON.parse(auditReport.detected_patterns_json).map((pat) => (
                      <span
                        key={pat}
                        className="text-[10px] font-semibold bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200"
                      >
                        {pat}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Interaction Timeline Stream */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3">
                Chronological Turn Sequence
              </h3>

              {(!selectedConvDetail || !selectedConvDetail.interactions || selectedConvDetail.interactions.length === 0) && (
                <p className="text-xs text-slate-400 italic text-center py-6">
                  Select a session to inspect interaction telemetry.
                </p>
              )}

              {selectedConvDetail?.interactions?.map((it) => (
                <div key={it.id} className="relative pl-6 pb-6 border-l-2 border-slate-200 last:border-l-transparent last:pb-0">
                  <div className="absolute -left-2.5 top-0 w-5 h-5 rounded-full bg-navy-800 text-white flex items-center justify-center text-[10px] font-bold">
                    {it.sequence_number}
                  </div>

                  <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-900">User Prompt:</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          it.guard_decision === 'ALLOW'
                            ? 'bg-emerald-100 text-emerald-800'
                            : it.guard_decision === 'LIMIT'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {it.guard_decision}
                      </span>
                    </div>
                    <p className="text-xs text-slate-800 font-medium italic">"{it.user_request}"</p>

                    {it.guard_explanation && (
                      <div className="text-[11px] text-slate-600 bg-white p-2.5 rounded-lg border border-slate-100">
                        <strong className="text-slate-800">Policy Reason: </strong>
                        {it.guard_explanation}
                      </div>
                    )}

                    <div className="mt-2 text-xs text-slate-700 bg-white p-3 rounded-lg border border-slate-100">
                      <strong className="text-slate-900 block mb-1">Simulated Response:</strong>
                      <p className="text-xs text-slate-600 line-clamp-3">{it.agent_response}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Scenario Testbed Runner */}
      {activeTab === 'scenarios' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Evaluation Scenario Catalogue</h3>
              <p className="text-xs text-slate-500">
                Pre-packaged testbed covering Single-Turn and Multi-Turn institutional safety scenarios.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={scenarioFilter}
                onChange={(e) => setScenarioFilter(e.target.value)}
                className="text-xs bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-slate-700 font-medium"
              >
                <option value="all">All Roles & Types ({scenarios.length})</option>
                <option value="student">Student (ST01-ST12)</option>
                <option value="ta">Teaching Assistant (TA01-TA10)</option>
                <option value="professor">Professor (PR01-PR10)</option>
                <option value="admin">Administrator (AD01-AD07)</option>
                <option value="auditor">Multi-Turn Auditor (AU01-AU12)</option>
              </select>
              <button
                onClick={runAllScenarios}
                disabled={runningScenarios}
                className="flex items-center gap-2 px-4 py-2 bg-navy-800 hover:bg-navy-900 disabled:bg-slate-300 text-white text-xs font-semibold rounded-xl shadow-sm transition"
              >
                <Play size={14} className={runningScenarios ? 'animate-spin' : ''} />
                <span>{runningScenarios ? 'Running Benchmark...' : 'Run All Filtered'}</span>
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-bold border-b border-slate-200">
                <tr>
                  <th className="p-3">Scenario ID</th>
                  <th className="p-3">Category / Role</th>
                  <th className="p-3">Title</th>
                  <th className="p-3">Expected Outcome</th>
                  <th className="p-3">Actual Result</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredScenarios.map((sc) => {
                  const runRes = scenarioResults[sc.id];
                  const isRunning = runningSingle === sc.id || runningScenarios;

                  return (
                    <tr key={sc.id} className="hover:bg-slate-50/70 transition">
                      <td className="p-3 font-bold text-navy-800">{sc.id}</td>
                      <td className="p-3">
                        <span className="capitalize px-2 py-0.5 rounded font-medium bg-slate-100 text-slate-700">
                          {sc.category}
                        </span>
                      </td>
                      <td className="p-3 font-medium text-slate-800">{sc.title}</td>
                      <td className="p-3">
                        <span className="font-semibold text-slate-600">
                          {sc.expected_decision || sc.expected_audit_label}
                        </span>
                      </td>
                      <td className="p-3">
                        {runRes ? (
                          <span
                            className={`inline-flex items-center gap-1 font-bold ${
                              runRes.passed ? 'text-emerald-600' : 'text-rose-600'
                            }`}
                          >
                            {runRes.passed ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                            {runRes.actual_decision || runRes.actual_audit_label}
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">Not executed</span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={() => runSingleScenario(sc.id)}
                          disabled={isRunning}
                          className="px-2.5 py-1 bg-slate-100 hover:bg-navy-800 hover:text-white rounded-lg text-slate-700 font-semibold transition"
                        >
                          Run
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: Policy Configuration */}
      {activeTab === 'policies' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Institutional Policy Rules</h3>
              <p className="text-xs text-slate-500">
                Loaded policy records gating individual and multi-turn educational interactions.
              </p>
            </div>
            <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1 rounded-full">
              {policies.length} Active Policies
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {policies.map((pol) => (
              <div key={pol.policy_id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-navy-800 text-xs">{pol.policy_id}</span>
                  <span className="text-[10px] font-bold uppercase bg-slate-200 px-2 py-0.5 rounded text-slate-700">
                    Role: {pol.role}
                  </span>
                </div>
                <h4 className="text-xs font-bold text-slate-900">{pol.title}</h4>
                <p className="text-xs text-slate-600 leading-relaxed">{pol.description}</p>
                <div className="text-[11px] text-slate-400 pt-1 flex items-center justify-between border-t border-slate-200">
                  <span>Scope: {pol.scope}</span>
                  <span>Version: v{pol.version}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
