import React from 'react';

export default function StatusBadge({ status, label }) {
  const norm = (status || '').toLowerCase();
  const text = label || status;

  let style = 'bg-slate-100 text-slate-700 border-slate-200';

  if (['graded', 'finished', 'published', 'allow', 'active', 'completed'].includes(norm)) {
    style = 'bg-emerald-50 text-emerald-800 border-emerald-200';
  } else if (['submitted', 'in_progress', 'draft', 'pending'].includes(norm)) {
    style = 'bg-amber-50 text-amber-800 border-amber-200';
  } else if (['unsubmitted', 'block', 'inactive', 'failed', 'overdue'].includes(norm)) {
    style = 'bg-rose-50 text-rose-800 border-rose-200';
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${style}`}
    >
      {text}
    </span>
  );
}
