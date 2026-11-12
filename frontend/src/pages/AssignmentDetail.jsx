import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import {
  ClipboardList,
  Calendar,
  Award,
  Send,
  AlertCircle,
  CheckCircle,
  Clock,
  User,
  Edit3,
} from 'lucide-react';

export default function AssignmentDetail() {
  const { id } = useParams();
  const { user, isStudent, isTeacher, isAdmin } = useAuth();
  const [assignment, setAssignment] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [submissionContent, setSubmissionContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Grading modal state
  const [gradingSubmission, setGradingSubmission] = useState(null);
  const [inputGrade, setInputGrade] = useState('');
  const [inputFeedback, setInputFeedback] = useState('');
  const [gradeError, setGradeError] = useState('');

  const loadAssignmentData = async () => {
    try {
      setLoading(true);
      setError('');
      const assignRes = await api.get(`/assignments/${id}`);
      setAssignment(assignRes.data);

      if (assignRes.data.my_submission) {
        setSubmissionContent(assignRes.data.my_submission.content);
      }

      // If staff in course, fetch course submissions
      const courseRole = assignRes.data.current_user_role || (isStudent ? 'student' : (isTeacher ? 'professor' : 'admin'));
      if (courseRole !== 'student') {
        try {
          const subRes = await api.get(`/assignments/${id}/submissions`);
          setSubmissions(subRes.data);
        } catch (subErr) {
          console.error("Could not load submissions list:", subErr);
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load assignment details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAssignmentData();
  }, [id]);

  const handleSubmitResponse = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    try {
      await api.post(`/assignments/${id}/submit`, {
        content: submissionContent,
      });
      setSuccessMsg('Assignment submitted successfully!');
      loadAssignmentData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit assignment.');
    }
  };

  const handleOpenGradeModal = (sub) => {
    setGradingSubmission(sub);
    setInputGrade(sub.grade !== null ? String(sub.grade) : '');
    setInputFeedback(sub.feedback || '');
    setGradeError('');
  };

  const handleSaveGrade = async (e) => {
    e.preventDefault();
    setGradeError('');

    const maxGrade = assignment?.max_grade || 100;
    const numericGrade = parseFloat(inputGrade);
    if (isNaN(numericGrade) || numericGrade < 0 || numericGrade > maxGrade) {
      setGradeError(`Grade must be a number between 0 and ${maxGrade}.`);
      return;
    }

    try {
      await api.post(`/submissions/${gradingSubmission.id}/grade`, {
        grade: numericGrade,
        feedback: inputFeedback,
      });
      setGradingSubmission(null);
      loadAssignmentData();
    } catch (err) {
      setGradeError(err.response?.data?.detail || 'Failed to record grade.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error && !assignment) {
    return (
      <div className="space-y-6">
        <Breadcrumbs items={[{ to: '/assignments', label: 'Assignments' }, { label: 'Error' }]} />
        <div className="p-8 bg-white border border-red-200 rounded-2xl shadow-sm text-center max-w-lg mx-auto">
          <AlertCircle size={32} className="text-red-600 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-slate-900 mb-2">Access Denied</h2>
          <p className="text-sm text-slate-600 mb-4">{error}</p>
          <Link to="/assignments" className="px-4 py-2 bg-navy-800 text-white rounded-lg text-xs font-semibold">
            Return to Assignments
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
          { to: `/courses/${assignment.course_id}`, label: assignment.course_code },
          { to: '/assignments', label: 'Assignments' },
          { label: assignment.title },
        ]}
      />

      {/* Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-navy-100 text-navy-800">
                {assignment.course_code}
              </span>
              <span className="text-xs text-slate-500 font-medium flex items-center gap-1">
                <Calendar size={13} className="text-slate-400" />
                Due: <strong>{assignment.due_date}</strong>
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900">{assignment.title}</h1>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-xl px-5 py-3 text-center shrink-0">
            <span className="text-xs text-slate-500 font-semibold uppercase block">Maximum Grade</span>
            <span className="text-2xl font-black text-navy-900">{assignment.max_grade} pts</span>
          </div>
        </div>

        <div className="prose prose-sm max-w-none text-slate-600 pt-4 border-t border-slate-100">
          <h4 className="font-bold text-slate-800 text-sm mb-1">Description</h4>
          <p className="mb-4">{assignment.description}</p>
          {assignment.instructions && (
            <>
              <h4 className="font-bold text-slate-800 text-sm mb-1">Submission Instructions</h4>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 font-mono text-xs text-slate-700 whitespace-pre-wrap">
                {assignment.instructions}
              </div>
            </>
          )}
        </div>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-sm flex items-center gap-2">
          <CheckCircle size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* ===================== STUDENT SUBMISSION SECTION ===================== */}
      {(assignment?.current_user_role ? assignment.current_user_role === 'student' : isStudent) && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm" data-testid="student-submission-container">
          <h2 className="text-lg font-bold text-slate-900 mb-4">Your Submission</h2>

          {assignment.my_submission && assignment.my_submission.grade !== null && (
            <div className="mb-6 p-5 rounded-xl bg-emerald-50 border border-emerald-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-emerald-900 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle size={16} className="text-emerald-700" />
                  Graded Submission
                </span>
                <span className="text-lg font-extrabold text-emerald-900">
                  {assignment.my_submission.grade} / {assignment.max_grade}
                </span>
              </div>
              {assignment.my_submission.feedback && (
                <div className="mt-2 text-xs text-emerald-800">
                  <strong>Instructor Feedback:</strong> {assignment.my_submission.feedback}
                </div>
              )}
            </div>
          )}

          <form onSubmit={handleSubmitResponse} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-2">
                Response / Source Deliverable Text:
              </label>
              <textarea
                rows="6"
                required
                disabled={assignment.my_submission?.grade !== null}
                value={submissionContent}
                onChange={(e) => setSubmissionContent(e.target.value)}
                data-testid="assignment-submission-input"
                placeholder="Enter or paste your assignment solution text here..."
                className="w-full p-4 border border-slate-300 rounded-xl text-sm font-mono focus:outline-none focus:ring-2 focus:ring-navy-800 disabled:bg-slate-100 disabled:text-slate-500"
              ></textarea>
            </div>

            {assignment.my_submission?.grade === null && (
              <div className="flex justify-end">
                <button
                  type="submit"
                  data-testid="submit-assignment-btn"
                  className="px-6 py-2.5 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors"
                >
                  <Send size={14} />
                  <span>{assignment.my_submission ? 'Resubmit Assignment' : 'Submit Assignment'}</span>
                </button>
              </div>
            )}
          </form>
        </div>
      )}

      {/* ===================== TEACHER / ADMIN SUBMISSIONS ROSTER ===================== */}
      {!(assignment?.current_user_role ? assignment.current_user_role === 'student' : isStudent) && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm" data-testid="teacher-submissions-roster">
          <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-800 text-base">Student Submissions Queue</h3>
              <p className="text-xs text-slate-500 mt-0.5">Submissions enrolled in {assignment.course_code}</p>
            </div>
            <span className="text-xs font-semibold text-slate-600 bg-slate-200/70 px-2.5 py-1 rounded-full">
              {submissions.length} Submissions
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600" data-testid="assignment-submissions-table">
              <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-6">Student</th>
                  <th className="py-3 px-6">Submission Preview</th>
                  <th className="py-3 px-6">Status</th>
                  <th className="py-3 px-6">Grade</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {submissions.map((sub) => (
                  <tr key={sub.id} className="hover:bg-slate-50/50" data-testid={`submission-row-${sub.id}`}>
                    <td className="py-4 px-6 font-bold text-slate-900">
                      {sub.student_name}
                      <span className="text-xs text-slate-400 block font-normal">Student ID: #{sub.student_id}</span>
                    </td>
                    <td className="py-4 px-6 max-w-xs truncate text-xs font-mono text-slate-600">
                      {sub.content}
                    </td>
                    <td className="py-4 px-6">
                      <StatusBadge status={sub.status} />
                    </td>
                    <td className="py-4 px-6 font-bold">
                      {sub.grade !== null ? (
                        <span className="text-emerald-700">{sub.grade} / {sub.max_grade}</span>
                      ) : (
                        <span className="text-slate-400 italic font-normal">Ungraded</span>
                      )}
                    </td>
                    <td className="py-4 px-6 text-right">
                      <button
                        onClick={() => handleOpenGradeModal(sub)}
                        data-testid={`grade-submission-btn-${sub.id}`}
                        className="px-3.5 py-1.5 bg-navy-800 hover:bg-navy-900 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1 transition-colors shadow-sm"
                      >
                        <Award size={12} />
                        <span>{sub.grade !== null ? 'Edit Grade' : 'Grade'}</span>
                      </button>
                    </td>
                  </tr>
                ))}
                {submissions.length === 0 && (
                  <tr>
                    <td colSpan="5" className="py-8 text-center text-xs text-slate-400 italic">
                      No submissions recorded for this assignment yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Grade Editing Modal */}
      <Modal
        isOpen={!!gradingSubmission}
        onClose={() => setGradingSubmission(null)}
        title={`Grade Submission — ${gradingSubmission?.student_name}`}
      >
        {gradeError && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200" data-testid="grading-error-message">
            {gradeError}
          </div>
        )}

        {gradingSubmission && (
          <form onSubmit={handleSaveGrade} className="space-y-4">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 max-h-36 overflow-y-auto font-mono">
              <strong className="block text-slate-900 mb-1">Student Solution Text:</strong>
              {gradingSubmission.content}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Score (0 to 100)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                required
                value={inputGrade}
                onChange={(e) => setInputGrade(e.target.value)}
                data-testid="grade-input"
                placeholder="e.g. 88"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Feedback to Student
              </label>
              <textarea
                rows="3"
                value={inputFeedback}
                onChange={(e) => setInputFeedback(e.target.value)}
                data-testid="feedback-input"
                placeholder="Constructive evaluation notes..."
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
              ></textarea>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setGradingSubmission(null)}
                className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                data-testid="save-grade-btn"
                className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-lg text-xs font-semibold"
              >
                Save Evaluation
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
