import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import { FileCheck2, Clock, CheckCircle2, AlertCircle, ArrowRight, ArrowLeft } from 'lucide-react';

export default function QuizAttempt() {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState(null);
  const [quiz, setQuiz] = useState(null);
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchAttemptInfo = async () => {
      try {
        setLoading(true);
        // We know attempt ID; we can load quiz attempts or quiz info
        // Let's get quiz info
        // Try getting attempts for student or fetch quizzes
        const meRes = await api.get('/auth/me');
        // Fetch all quizzes to locate attempt's quiz
        const coursesRes = await api.get('/courses');
        let matchedQuiz = null;
        for (const c of coursesRes.data) {
          const qRes = await api.get(`/courses/${c.id}/quizzes`);
          for (const q of qRes.data) {
            const atts = await api.get(`/quizzes/${q.id}/attempts`);
            const matchedAtt = atts.data.find(a => a.id === parseInt(attemptId, 10));
            if (matchedAtt) {
              setAttempt(matchedAtt);
              matchedQuiz = q;
              break;
            }
          }
          if (matchedQuiz) break;
        }

        if (matchedQuiz) {
          // Fetch full quiz with questions
          const fullQuiz = await api.get(`/quizzes/${matchedQuiz.id}`);
          setQuiz(fullQuiz.data);
        } else {
          setError('Quiz attempt could not be identified or accessed.');
        }
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to initialize quiz assessment.');
      } finally {
        setLoading(false);
      }
    };

    fetchAttemptInfo();
  }, [attemptId]);

  const handleSelectOption = (questionId, option) => {
    setSelectedAnswers((prev) => ({
      ...prev,
      [questionId]: option,
    }));
  };

  const handleSubmitQuiz = async (e) => {
    e.preventDefault();
    if (!quiz) return;

    setError('');
    setSubmitting(true);

    const answersPayload = (quiz.questions || []).map((q) => ({
      question_id: q.id,
      selected_option: selectedAnswers[q.id] || '',
    }));

    try {
      const res = await api.post(`/attempts/${attemptId}/submit`, {
        answers: answersPayload,
      });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit quiz attempt.');
    } finally {
      setSubmitting(false);
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
        <div className="p-8 bg-white border border-red-200 rounded-2xl shadow-sm text-center max-w-lg mx-auto">
          <AlertCircle size={32} className="text-red-600 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-slate-900 mb-2">Error</h2>
          <p className="text-sm text-slate-600 mb-4">{error}</p>
          <Link to="/quizzes" className="px-4 py-2 bg-navy-800 text-white rounded-lg text-xs font-semibold">
            Return to Quizzes
          </Link>
        </div>
      </div>
    );
  }

  // If already completed / submitted
  if (result || attempt?.status === 'finished') {
    const finalScore = result ? result.score : attempt.score;
    return (
      <div className="max-w-2xl mx-auto space-y-6 py-8">
        <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm text-center" data-testid="quiz-completion-card">
          <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 size={36} />
          </div>
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
            Assessment Completed
          </span>
          <h1 className="text-2xl font-extrabold text-slate-900">{quiz.title}</h1>
          <p className="text-sm text-slate-500 mt-1">Your responses have been evaluated and recorded.</p>

          <div className="my-8 p-6 bg-slate-50 rounded-2xl border border-slate-200 max-w-sm mx-auto">
            <span className="text-xs font-semibold text-slate-500 uppercase block">Your Score</span>
            <span className="text-4xl font-black text-navy-900 mt-1 block" data-testid="quiz-final-score">
              {finalScore}%
            </span>
            <span className="text-xs text-emerald-700 font-semibold mt-1 block">Attempt Finished</span>
          </div>

          <Link
            to={`/quizzes/${quiz.id}`}
            data-testid="return-to-quiz-btn"
            className="px-6 py-2.5 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold inline-flex items-center gap-2 shadow-sm transition-colors"
          >
            <span>Return to Quiz Details</span>
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Breadcrumbs
        items={[
          { to: '/quizzes', label: 'Quizzes' },
          { to: `/quizzes/${quiz.id}`, label: quiz.title },
          { label: `Attempt #${attempt?.attempt_number || 1}` },
        ]}
      />

      {/* Quiz Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex items-center justify-between">
        <div>
          <span className="text-xs font-bold uppercase text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
            Active Attempt
          </span>
          <h1 className="text-xl font-bold text-slate-900 mt-1">{quiz.title}</h1>
        </div>
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-100 text-slate-700 text-xs font-mono font-semibold">
          <Clock size={15} className="text-slate-500" />
          <span>{quiz.time_limit_minutes} Min Assessment</span>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Questions Form */}
      <form onSubmit={handleSubmitQuiz} className="space-y-6" data-testid="quiz-attempt-form">
        {(quiz.questions || []).map((q, idx) => (
          <div
            key={q.id}
            data-testid={`question-container-${q.id}`}
            className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-4"
          >
            <div className="flex items-start justify-between gap-4">
              <span className="px-2.5 py-1 rounded-lg bg-navy-100 text-navy-800 text-xs font-bold shrink-0">
                Question {idx + 1}
              </span>
              <span className="text-xs text-slate-400 font-semibold">{q.points} Points</span>
            </div>

            <p className="text-base font-semibold text-slate-800 leading-relaxed">
              {q.question_text}
            </p>

            <div className="space-y-2.5 pt-2">
              {q.options.map((opt, oIdx) => {
                const isSelected = selectedAnswers[q.id] === opt;
                return (
                  <label
                    key={oIdx}
                    data-testid={`question-${q.id}-option-${oIdx}`}
                    className={`flex items-center gap-3 p-3.5 rounded-xl border cursor-pointer text-sm font-medium transition-all ${
                      isSelected
                        ? 'border-navy-800 bg-navy-50/50 text-navy-950 font-semibold shadow-xs'
                        : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <input
                      type="radio"
                      name={`question_${q.id}`}
                      value={opt}
                      checked={isSelected}
                      onChange={() => handleSelectOption(q.id, opt)}
                      className="w-4 h-4 text-navy-800 focus:ring-navy-800 border-slate-300"
                    />
                    <span>{opt}</span>
                  </label>
                );
              })}
            </div>
          </div>
        ))}

        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex items-center justify-between">
          <Link
            to={`/quizzes/${quiz.id}`}
            className="px-4 py-2 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <ArrowLeft size={14} />
            <span>Cancel Attempt</span>
          </Link>
          <button
            type="submit"
            disabled={submitting}
            data-testid="submit-quiz-attempt-btn"
            className="px-6 py-2.5 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-md transition-colors disabled:opacity-50"
          >
            <span>{submitting ? 'Submitting...' : 'Submit Assessment'}</span>
            <CheckCircle2 size={16} />
          </button>
        </div>
      </form>
    </div>
  );
}
