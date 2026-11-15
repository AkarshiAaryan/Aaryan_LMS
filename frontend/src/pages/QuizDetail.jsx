import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import StatusBadge from '../components/StatusBadge';
import {
  FileCheck2,
  Clock,
  RotateCcw,
  Play,
  AlertCircle,
  CheckCircle,
  ArrowRight,
  HelpCircle,
  Award,
} from 'lucide-react';

export default function QuizDetail() {
  const { id } = useParams();
  const { user, isStudent, isTeacher, isAdmin } = useAuth();
  const [quiz, setQuiz] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);
  const navigate = useNavigate();

  const loadQuizData = async () => {
    try {
      setLoading(true);
      setError('');
      const [quizRes, attemptsRes] = await Promise.all([
        api.get(`/quizzes/${id}`),
        api.get(`/quizzes/${id}/attempts`),
      ]);
      setQuiz(quizRes.data);
      setAttempts(attemptsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load quiz details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuizData();
  }, [id]);

  const handleStartAttempt = async () => {
    setError('');
    setStarting(true);
    try {
      const res = await api.post(`/quizzes/${id}/attempts`);
      navigate(`/attempts/${res.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Cannot start quiz attempt.');
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error && !quiz) {
    return (
      <div className="space-y-6">
        <Breadcrumbs items={[{ to: '/quizzes', label: 'Quizzes' }, { label: 'Error' }]} />
        <div className="p-8 bg-white border border-red-200 rounded-2xl shadow-sm text-center max-w-lg mx-auto">
          <AlertCircle size={32} className="text-red-600 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-slate-900 mb-2">Access Forbidden</h2>
          <p className="text-sm text-slate-600 mb-4">{error}</p>
          <Link to="/quizzes" className="px-4 py-2 bg-navy-800 text-white rounded-lg text-xs font-semibold">
            Return to Quizzes
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { to: '/courses', label: 'Courses' },
          { to: `/courses/${quiz.course_id}`, label: quiz.course_code },
          { to: '/quizzes', label: 'Quizzes' },
          { label: quiz.title },
        ]}
      />

      {/* Quiz Header Information */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-navy-100 text-navy-800">
                {quiz.course_code}
              </span>
              <span className="text-xs text-slate-500 font-medium flex items-center gap-1">
                <Clock size={13} className="text-slate-400" />
                Time Limit: <strong>{quiz.time_limit_minutes} minutes</strong>
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900">{quiz.title}</h1>
            <p className="text-sm text-slate-600 mt-2 max-w-2xl">{quiz.description}</p>
          </div>

          {/* Start Quiz Action (Student Only) */}
          {(quiz.current_user_role ? quiz.current_user_role === 'student' : isStudent) && (
            <div className="text-right shrink-0">
              <button
                onClick={handleStartAttempt}
                disabled={starting}
                data-testid="start-quiz-btn"
                className="px-6 py-3 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-sm font-bold flex items-center gap-2 shadow-md transition-colors disabled:opacity-50"
              >
                <Play size={16} />
                <span>{starting ? 'Starting...' : 'Attempt Quiz Now'}</span>
              </button>
              <p className="text-xs text-slate-400 mt-1.5 font-medium">
                Attempts Remaining: <span className="font-bold text-slate-700">{quiz.attempts_remaining}</span> of {quiz.max_attempts}
              </p>
            </div>
          )}
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2 mb-4" data-testid="quiz-attempt-limit-error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-6 border-t border-slate-100 text-center">
          <div className="p-3 bg-slate-50 rounded-xl">
            <span className="text-xs text-slate-400 uppercase font-semibold block">Questions</span>
            <span className="text-lg font-bold text-slate-800">{quiz.question_count || quiz.questions?.length || 2}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl">
            <span className="text-xs text-slate-400 uppercase font-semibold block">Max Attempts</span>
            <span className="text-lg font-bold text-slate-800">{quiz.max_attempts}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl">
            <span className="text-xs text-slate-400 uppercase font-semibold block">Window Opens</span>
            <span className="text-xs font-bold text-slate-800">{quiz.open_date}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl">
            <span className="text-xs text-slate-400 uppercase font-semibold block">Window Closes</span>
            <span className="text-xs font-bold text-slate-800">{quiz.close_date}</span>
          </div>
        </div>
      </div>

      {/* Attempts History */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm" data-testid="quiz-attempts-container">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h3 className="font-bold text-slate-800 text-base">
            {(quiz.current_user_role ? quiz.current_user_role === 'student' : isStudent) ? 'Your Previous Attempts' : 'Student Quiz Attempt Records'}
          </h3>
          <span className="text-xs text-slate-500 font-semibold">{attempts.length} Attempt(s) Logged</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600" data-testid="quiz-attempts-table">
            <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
              <tr>
                {!(quiz.current_user_role ? quiz.current_user_role === 'student' : isStudent) && <th className="py-3 px-6">Student</th>}
                <th className="py-3 px-6">Attempt #</th>
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-6">Score</th>
                <th className="py-3 px-6 text-right">Completion Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {attempts.map((att) => (
                <tr key={att.id} className="hover:bg-slate-50/50" data-testid={`attempt-row-${att.id}`}>
                  {!(quiz.current_user_role ? quiz.current_user_role === 'student' : isStudent) && (
                    <td className="py-4 px-6 font-bold text-slate-900">
                      {att.student_name}
                      <span className="text-xs text-slate-400 block font-normal">Student ID #{att.student_id}</span>
                    </td>
                  )}
                  <td className="py-4 px-6 font-semibold text-slate-800">
                    Attempt {att.attempt_number}
                  </td>
                  <td className="py-4 px-6">
                    <StatusBadge status={att.status} />
                  </td>
                  <td className="py-4 px-6 font-extrabold text-navy-900">
                    {att.score !== null ? `${att.score}%` : 'In Progress'}
                  </td>
                  <td className="py-4 px-6 text-right text-xs text-slate-500">
                    {att.completed_at ? new Date(att.completed_at).toLocaleString() : 'Incomplete'}
                  </td>
                </tr>
              ))}
              {attempts.length === 0 && (
                <tr>
                  <td colSpan={!(quiz.current_user_role ? quiz.current_user_role === 'student' : isStudent) ? 5 : 4} className="py-8 text-center text-slate-400 text-xs italic">
                    No attempts have been logged for this quiz yet.
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
