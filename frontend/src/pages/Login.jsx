import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { GraduationCap, Lock, User, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';

export default function Login() {
  const [username, setUsername] = useState('student01');
  const [password, setPassword] = useState('GuardSLM2026!');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Authentication failed. Please verify credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  const setDemoAccount = (uname) => {
    setUsername(uname);
    setPassword('GuardSLM2026!');
    setError('');
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center items-center p-4">
      {/* Container */}
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
        {/* Academic Header Banner */}
        <div className="bg-navy-900 px-8 py-8 text-center text-white">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/10 backdrop-blur-md mb-3 text-white border border-white/20">
            <GraduationCap size={32} />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight">GuardSLM LMS</h1>
          <p className="text-slate-300 text-xs mt-1 uppercase tracking-wider font-semibold">
            Browser Authorization Research Environment
          </p>
        </div>

        {/* Login Form */}
        <div className="p-8">
          {error && (
            <div
              className="mb-5 p-3.5 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-start gap-2.5 animate-in fade-in"
              role="alert"
              data-testid="login-error-message"
            >
              <AlertCircle size={18} className="shrink-0 mt-0.5 text-red-600" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5" htmlFor="username">
                Username
              </label>
              <div className="relative">
                <User size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  id="username"
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  data-testid="login-username-input"
                  placeholder="e.g. admin, teacher1, student1"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-navy-800 focus:bg-white transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5" htmlFor="password">
                Password
              </label>
              <div className="relative">
                <Lock size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  data-testid="login-password-input"
                  placeholder="Enter your password"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-navy-800 focus:bg-white transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              data-testid="login-submit-button"
              className="w-full mt-2 py-3 px-4 bg-navy-800 hover:bg-navy-900 text-white font-semibold text-sm rounded-xl shadow-md transition-colors flex items-center justify-center gap-2 disabled:opacity-70"
            >
              {loading ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <span>Sign In to Dashboard</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Accounts Selection */}
          <div className="mt-6 pt-6 border-t border-slate-200">
            <p className="text-xs font-semibold text-slate-500 mb-2 flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-indigo-600" />
              <span>Select Pre-seeded Academic Persona:</span>
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 text-xs max-h-56 overflow-y-auto p-1">
              <button
                type="button"
                onClick={() => setDemoAccount('admin01')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-admin01"
              >
                <span className="font-bold text-red-700 block">admin01</span>
                <span className="text-[10px] text-slate-500 block truncate">Alex Admin (Admin)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('prof01')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-prof01"
              >
                <span className="font-bold text-indigo-700 block">prof01</span>
                <span className="text-[10px] text-slate-500 block truncate">Dr Mira Shah (301, 303)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('prof02')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-prof02"
              >
                <span className="font-bold text-indigo-700 block">prof02</span>
                <span className="text-[10px] text-slate-500 block truncate">Dr Kabir Rao (302, 401)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('ta01')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-ta01"
              >
                <span className="font-bold text-amber-700 block">ta01</span>
                <span className="text-[10px] text-slate-500 block truncate">Sam Lee (TA:301/Stu:302)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('ta02')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-ta02"
              >
                <span className="font-bold text-amber-700 block">ta02</span>
                <span className="text-[10px] text-slate-500 block truncate">Noor Khan (TA:302, 401)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('ta03')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-ta03"
              >
                <span className="font-bold text-amber-700 block">ta03</span>
                <span className="text-[10px] text-slate-500 block truncate">Dev Patel (TA:303)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('ta04')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-ta04"
              >
                <span className="font-bold text-amber-700 block">ta04</span>
                <span className="text-[10px] text-slate-500 block truncate">Elena Rostova (TA:303/Stu:301)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student01')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student01"
              >
                <span className="font-bold text-emerald-700 block">student01</span>
                <span className="text-[10px] text-slate-500 block truncate">Asha Mehta (All 4)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student02')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student02"
              >
                <span className="font-bold text-emerald-700 block">student02</span>
                <span className="text-[10px] text-slate-500 block truncate">Rohan Das (301, 302)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student03')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student03"
              >
                <span className="font-bold text-emerald-700 block">student03</span>
                <span className="text-[10px] text-slate-500 block truncate">Isha Roy (301, 401)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student04')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student04"
              >
                <span className="font-bold text-emerald-700 block">student04</span>
                <span className="text-[10px] text-slate-500 block truncate">Vikram Sen (302, 303)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student05')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student05"
              >
                <span className="font-bold text-emerald-700 block">student05</span>
                <span className="text-[10px] text-slate-500 block truncate">Tara Bose (303, 401)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student06')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student06"
              >
                <span className="font-bold text-emerald-700 block">student06</span>
                <span className="text-[10px] text-slate-500 block truncate">Arjun Nair (All 4)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student07')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student07"
              >
                <span className="font-bold text-emerald-700 block">student07</span>
                <span className="text-[10px] text-slate-500 block truncate">Priya Sharma (301, 401)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student08')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student08"
              >
                <span className="font-bold text-emerald-700 block">student08</span>
                <span className="text-[10px] text-slate-500 block truncate">Marcus Chen (301, 302, 303)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student09')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student09"
              >
                <span className="font-bold text-emerald-700 block">student09</span>
                <span className="text-[10px] text-slate-500 block truncate">Fatima Zahra (302, 401)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student10')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student10"
              >
                <span className="font-bold text-emerald-700 block">student10</span>
                <span className="text-[10px] text-slate-500 block truncate">Lucas Silva (301, 303)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student11')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student11"
              >
                <span className="font-bold text-emerald-700 block">student11</span>
                <span className="text-[10px] text-slate-500 block truncate">Chloe Bennett (302, 303, 401)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student12')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student12"
              >
                <span className="font-bold text-emerald-700 block">student12</span>
                <span className="text-[10px] text-slate-500 block truncate">David Kim (301, 302)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student13')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student13"
              >
                <span className="font-bold text-emerald-700 block">student13</span>
                <span className="text-[10px] text-slate-500 block truncate">Ananya Iyer (All 4)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student14')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student14"
              >
                <span className="font-bold text-emerald-700 block">student14</span>
                <span className="text-[10px] text-slate-500 block truncate">Omar Farooq (303)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student15')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student15"
              >
                <span className="font-bold text-emerald-700 block">student15</span>
                <span className="text-[10px] text-slate-500 block truncate">Sofia Morales (301, 401)</span>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('student16')}
                className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-left transition-colors"
                data-testid="demo-account-student16"
              >
                <span className="font-bold text-emerald-700 block">student16</span>
                <span className="text-[10px] text-slate-500 block truncate">Kevin Zhao (302, 303)</span>
              </button>
            </div>
            <p className="text-[11px] text-slate-400 text-center mt-3">
              Standard demo password: <code className="font-mono text-slate-600 bg-slate-100 px-1 py-0.5 rounded">GuardSLM2026!</code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
