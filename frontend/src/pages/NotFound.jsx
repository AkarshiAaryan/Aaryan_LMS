import React from 'react';
import { Link } from 'react-router-dom';
import { HelpCircle, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-6">
      <div className="w-16 h-16 bg-slate-100 text-slate-500 rounded-full flex items-center justify-center mb-4">
        <HelpCircle size={36} />
      </div>
      <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">404 — Page Not Found</h1>
      <p className="text-sm text-slate-600 mt-2 max-w-md">
        The requested LMS page or resource does not exist in this fixture.
      </p>
      <Link
        to="/dashboard"
        className="mt-6 px-5 py-2.5 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold inline-flex items-center gap-2 shadow-sm transition-colors"
      >
        <ArrowLeft size={14} />
        <span>Return to Dashboard</span>
      </Link>
    </div>
  );
}
