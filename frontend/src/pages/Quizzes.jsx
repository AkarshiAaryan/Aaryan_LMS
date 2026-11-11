import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import StatusBadge from '../components/StatusBadge';
import { FileCheck2, Clock, RotateCcw, ArrowRight, AlertCircle } from 'lucide-react';

export default function Quizzes() {
  const { user, isStudent } = useAuth();
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchAllQuizzes = async () => {
      try {
        setLoading(true);
        const coursesRes = await api.get('/courses');
        const allQuizzes = [];
        for (const c of coursesRes.data) {
          try {
            const res = await api.get(`/courses/${c.id}/quizzes`);
            allQuizzes.push(...res.data);
          } catch (e) {
            console.error(`Error loading quizzes for course ${c.code}`, e);
          }
        }
        setQuizzes(allQuizzes);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to fetch quizzes.');
      } finally {
        setLoading(false);
      }
    };

    fetchAllQuizzes();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Quizzes' }]} />

      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-extrabold text-slate-900">Quizzes & Online Assessments</h1>
        <p className="text-sm text-slate-500 mt-1">
          Complete timed multiple-choice assessments and review attempt scores.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600" data-testid="quizzes-table">
            <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3.5 px-6">Quiz Title</th>
                <th className="py-3.5 px-6">Course</th>
                <th className="py-3.5 px-6">Time Limit</th>
                <th className="py-3.5 px-6">Max Attempts</th>
                {isStudent && <th className="py-3.5 px-6">Remaining</th>}
                <th className="py-3.5 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {quizzes.map((q) => (
                <tr key={q.id} className="hover:bg-slate-50/50 transition-colors" data-testid={`quiz-row-${q.id}`}>
                  <td className="py-4 px-6 font-bold text-slate-900">
                    <Link to={`/quizzes/${q.id}`} className="hover:text-indigo-600 transition-colors">
                      {q.title}
                    </Link>
                  </td>
                  <td className="py-4 px-6">
                    <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-navy-100 text-navy-800">
                      {q.course_code}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-xs text-slate-600">
                    <span className="flex items-center gap-1.5">
                      <Clock size={13} className="text-slate-400" />
                      {q.time_limit_minutes} mins
                    </span>
                  </td>
                  <td className="py-4 px-6 font-semibold text-slate-700">
                    {q.max_attempts}
                  </td>
                  {isStudent && (
                    <td className="py-4 px-6 font-bold">
                      <span className={q.attempts_remaining === 0 ? 'text-red-600' : 'text-emerald-700'}>
                        {q.attempts_remaining}
                      </span>
                    </td>
                  )}
                  <td className="py-4 px-6 text-right">
                    <Link
                      to={`/quizzes/${q.id}`}
                      data-testid={`open-quiz-btn-${q.id}`}
                      className="px-3.5 py-1.5 bg-navy-800 hover:bg-navy-900 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1 transition-colors shadow-sm"
                    >
                      <span>{isStudent ? 'Start / View' : 'Inspect'}</span>
                      <ArrowRight size={12} />
                    </Link>
                  </td>
                </tr>
              ))}
              {quizzes.length === 0 && (
                <tr>
                  <td colSpan={isStudent ? 6 : 5} className="py-12 text-center text-slate-400 text-xs italic">
                    No quizzes found for your courses.
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
