import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

export default function Breadcrumbs({ items = [] }) {
  const location = useLocation();

  return (
    <nav className="flex items-center text-xs text-slate-500 mb-4" aria-label="Breadcrumb">
      <Link to="/dashboard" className="flex items-center gap-1 hover:text-slate-800 transition-colors">
        <Home size={14} />
        <span>LMS</span>
      </Link>

      {items.map((item, idx) => (
        <React.Fragment key={idx}>
          <ChevronRight size={12} className="mx-2 text-slate-400" />
          {item.to ? (
            <Link to={item.to} className="hover:text-slate-800 transition-colors">
              {item.label}
            </Link>
          ) : (
            <span className="font-semibold text-slate-800" aria-current="page">
              {item.label}
            </span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}
