import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { Award, BookOpen, AlertCircle, Edit3, ArrowRight } from 'lucide-react';

export default function Gradebook() {
  const { user, isStudent, isTeacher, isAdmin } = useAuth();
  const [courses, setCourses] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState('');
  const [gradebookData, setGradebookData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Grade edit modal state (for teachers/admins)
  const [editSubmission, setEditSubmission] = useState(null);
  const [editGrade, setEditGrade] = useState('');
  const [editFeedback, setEditFeedback] = useState('');
  const [editError, setEditError] = useState('');

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        setLoading(true);
        const res = await api.get('/courses');
        setCourses(res.data);
        if (res.data.length > 0) {
          setSelectedCourseId(String(res.data[0].id));
        }
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to fetch courses.');
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, []);

  const loadGradebook = async (cid) => {
    if (!cid) return;
    try {
      setLoading(true);
      setError('');
      const res = await api.get(`/courses/${cid}/grades`);
      setGradebookData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Access forbidden: You cannot view this course gradebook.');
      setGradebookData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedCourseId) {
      loadGradebook(selectedCourseId);
    }
  }, [selectedCourseId]);

  const handleOpenEdit = (studentRow, item) => {
    if (!item.submission_id) return;
    setEditSubmission({
      id: item.submission_id,
      title: item.title,
      student_name: studentRow.student_name,
      score: item.score,
      feedback: item.feedback,
    });
    setEditGrade(item.score !== null ? String(item.score) : '');
    setEditFeedback(item.feedback || '');
    setEditError('');
  };

  const handleSaveGrade = async (e) => {
    e.preventDefault();
    setEditError('');

    const numericGrade = parseFloat(editGrade);
    if (isNaN(numericGrade) || numericGrade < 0 || numericGrade > 100) {
      setEditError('Grade must be a number between 0 and 100.');
      return;
    }

    try {
      await api.put(`/grades/${editSubmission.id}`, {
        grade: numericGrade,
        feedback: editFeedback,
      });
      setEditSubmission(null);
      loadGradebook(selectedCourseId);
    } catch (err) {
      setEditError(err.response?.data?.detail || 'Failed to update grade.');
    }
  };

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Gradebook' }]} />

      <div className="border-b border-slate-200 pb-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900">Academic Gradebook</h1>
          <p className="text-sm text-slate-500 mt-1">
            {isStudent
              ? 'Comprehensive record of your course performance and assessments.'
              : 'Course assessment records for enrolled students.'}
          </p>
        </div>

        {/* Course selector dropdown */}
        {courses.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-slate-500 uppercase">Course:</label>
            <select
              value={selectedCourseId}
              onChange={(e) => setSelectedCourseId(e.target.value)}
              data-testid="gradebook-course-select"
              className="px-3.5 py-2 bg-white border border-slate-300 rounded-xl text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-navy-800 shadow-sm"
            >
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} — {c.title}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2" data-testid="gradebook-error-message">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-24 text-slate-400">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      )}

      {!loading && gradebookData && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm" data-testid="gradebook-container">
          <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded text-xs font-extrabold bg-navy-100 text-navy-800">
                {gradebookData.course.code}
              </span>
              <h3 className="font-bold text-slate-800 text-sm">{gradebookData.course.title}</h3>
            </div>
            <span className="text-xs text-slate-500 font-semibold">
              {gradebookData.students.length} Student Record(s) Visible
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600" data-testid="gradebook-table">
              <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3.5 px-6">Student</th>
                  {gradebookData.assignments.map((a) => (
                    <th key={`a-${a.id}`} className="py-3.5 px-6">
                      {a.title} <span className="text-[10px] text-slate-400 block font-normal">Assignment (/100)</span>
                    </th>
                  ))}
                  {gradebookData.quizzes.map((q) => (
                    <th key={`q-${q.id}`} className="py-3.5 px-6">
                      {q.title} <span className="text-[10px] text-slate-400 block font-normal">Quiz (/100)</span>
                    </th>
                  ))}
                  <th className="py-3.5 px-6 text-right">Cumulative Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {gradebookData.students.map((st) => (
                  <tr key={st.student_id} className="hover:bg-slate-50/50 transition-colors" data-testid={`student-grade-row-${st.username}`}>
                    <td className="py-4 px-6 font-bold text-slate-900">
                      {st.student_name}
                      <span className="text-xs text-slate-400 font-mono block font-normal">@{st.username}</span>
                    </td>

                    {/* Assignment items */}
                    {gradebookData.assignments.map((a) => {
                      const item = st.items.find((i) => i.item_type === 'assignment' && i.item_id === a.id);
                      return (
                        <td key={`a-score-${a.id}`} className="py-4 px-6">
                          {item && item.score !== null ? (
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-emerald-700">{item.score}</span>
                              {!(gradebookData?.current_user_role ? gradebookData.current_user_role === 'student' : isStudent) && item.submission_id && (
                                <button
                                  onClick={() => handleOpenEdit(st, item)}
                                  data-testid={`edit-grade-btn-${item.submission_id}`}
                                  className="text-slate-400 hover:text-navy-800 transition-colors p-1"
                                  title="Edit Grade"
                                >
                                  <Edit3 size={13} />
                                </button>
                              )}
                            </div>
                          ) : (
                            <span className="text-xs text-slate-400 italic">Not graded</span>
                          )}
                        </td>
                      );
                    })}

                    {/* Quiz items */}
                    {gradebookData.quizzes.map((q) => {
                      const item = st.items.find((i) => i.item_type === 'quiz' && i.item_id === q.id);
                      return (
                        <td key={`q-score-${q.id}`} className="py-4 px-6">
                          {item && item.score !== null ? (
                            <span className="font-bold text-indigo-700">{item.score}</span>
                          ) : (
                            <span className="text-xs text-slate-400 italic">—</span>
                          )}
                        </td>
                      );
                    })}

                    <td className="py-4 px-6 text-right">
                      <span className="text-base font-extrabold text-navy-900" data-testid={`student-final-percentage-${st.username}`}>
                        {st.percentage}%
                      </span>
                    </td>
                  </tr>
                ))}
                {gradebookData.students.length === 0 && (
                  <tr>
                    <td colSpan={2 + gradebookData.assignments.length + gradebookData.quizzes.length} className="py-12 text-center text-xs text-slate-400 italic">
                      No grade records found for this course.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Grade Edit Modal */}
      <Modal
        isOpen={!!editSubmission}
        onClose={() => setEditSubmission(null)}
        title={`Edit Grade — ${editSubmission?.student_name}`}
      >
        {editError && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200">
            {editError}
          </div>
        )}

        {editSubmission && (
          <form onSubmit={handleSaveGrade} className="space-y-4">
            <p className="text-xs text-slate-600 font-medium">
              Assessment: <strong>{editSubmission.title}</strong>
            </p>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Score (0 to 100)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                required
                value={editGrade}
                onChange={(e) => setEditGrade(e.target.value)}
                data-testid="gradebook-grade-input"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Feedback
              </label>
              <textarea
                rows="3"
                value={editFeedback}
                onChange={(e) => setEditFeedback(e.target.value)}
                data-testid="gradebook-feedback-input"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
              ></textarea>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setEditSubmission(null)}
                className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                data-testid="save-gradebook-grade-btn"
                className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-lg text-xs font-semibold"
              >
                Save Grade
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
