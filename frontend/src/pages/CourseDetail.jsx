import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import StatusBadge from '../components/StatusBadge';
import {
  BookOpen,
  ClipboardList,
  FileCheck2,
  Award,
  FolderOpen,
  User,
  Users,
  Bell,
  ArrowRight,
  AlertCircle,
  Calendar,
  Shield,
  CheckCircle2,
  Lock,
  KeyRound,
  FileText,
} from 'lucide-react';

export default function CourseDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [course, setCourse] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Course contents
  const [assignments, setAssignments] = useState([]);
  const [quizzes, setQuizzes] = useState([]);
  const [resources, setResources] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [gradebookRows, setGradebookRows] = useState([]);
  const [publishing, setPublishing] = useState(false);
  const [publishMessage, setPublishMessage] = useState('');

  const fetchCourseData = async () => {
    try {
      setLoading(true);
      setError('');
      const [courseRes, assignRes, quizRes, resRes, annRes, polRes] = await Promise.all([
        api.get(`/courses/${id}`),
        api.get(`/courses/${id}/assignments`),
        api.get(`/courses/${id}/quizzes`),
        api.get(`/courses/${id}/resources`),
        api.get(`/courses/${id}/announcements`),
        api.get(`/courses/${id}/policies`),
      ]);

      setCourse(courseRes.data);
      setAssignments(assignRes.data);
      setQuizzes(quizRes.data);
      setResources(resRes.data);
      setAnnouncements(annRes.data);
      setPolicies(polRes.data);

      try {
        const gradesRes = await api.get(`/courses/${id}/grades`);
        setGradebookRows(gradesRes.data);
      } catch (gErr) {
        console.error("Gradebook fetch error:", gErr);
      }
    } catch (err) {
      setError(
        err.response?.data?.detail || 'You are not authorized to access this course.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourseData();
  }, [id]);

  const handlePublishGrades = async () => {
    try {
      setPublishing(true);
      setPublishMessage('');
      const res = await api.post(`/courses/${id}/publish-grades`, { is_published: true });
      setPublishMessage(res.data?.message || 'Final grades published successfully.');
      // Refresh grades
      const gradesRes = await api.get(`/courses/${id}/grades`);
      setGradebookRows(gradesRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to publish grades.');
    } finally {
      setPublishing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error && !course) {
    return (
      <div className="space-y-6">
        <Breadcrumbs items={[{ to: '/courses', label: 'Courses' }, { label: 'Access Denied' }]} />
        <div className="p-8 bg-white border border-red-200 rounded-2xl shadow-sm text-center max-w-lg mx-auto" data-testid="course-access-denied">
          <div className="w-14 h-14 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle size={30} />
          </div>
          <h2 className="text-xl font-bold text-slate-900 mb-2">Access Forbidden</h2>
          <p className="text-sm text-slate-600 mb-6">{error}</p>
          <Link
            to="/courses"
            className="px-5 py-2.5 bg-navy-800 text-white rounded-xl text-xs font-semibold hover:bg-navy-900 transition-colors inline-flex items-center gap-2"
          >
            <span>Return to My Courses</span>
          </Link>
        </div>
      </div>
    );
  }

  const roleInCourse = course.current_user_role;
  const isProfOrAdmin = roleInCourse === 'professor' || roleInCourse === 'admin';
  const isTA = roleInCourse === 'ta';
  const isStudent = roleInCourse === 'student';

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BookOpen },
    { id: 'assignments', label: `Assignments (${assignments.length})`, icon: ClipboardList },
    { id: 'quizzes', label: `Quizzes (${quizzes.length})`, icon: FileCheck2 },
    { id: 'grades', label: 'Grades', icon: Award },
    { id: 'resources', label: `Resources (${resources.length})`, icon: FolderOpen },
    { id: 'policies', label: `Policies (${policies.length})`, icon: FileText },
  ];

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ to: '/courses', label: 'Courses' }, { label: course.code }]} />

      {/* Course Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="px-3 py-1 rounded-lg text-xs font-extrabold bg-navy-100 text-navy-900 border border-navy-200">
                {course.code}
              </span>
              {/* Current user course-specific role badge */}
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                roleInCourse === 'professor' ? 'bg-indigo-100 text-indigo-800 border-indigo-200' :
                roleInCourse === 'ta' ? 'bg-amber-100 text-amber-800 border-amber-200' :
                roleInCourse === 'admin' ? 'bg-red-100 text-red-800 border-red-200' :
                'bg-emerald-100 text-emerald-800 border-emerald-200'
              }`} data-testid="course-role-badge">
                Your Role: {roleInCourse ? roleInCourse.toUpperCase() : 'NONE'}
              </span>

              <span className="text-xs text-slate-500 font-medium flex items-center gap-1.5 ml-2">
                <User size={13} className="text-slate-400" />
                Professor: <strong className="text-slate-700">{course.teacher_name}</strong>
              </span>
              {course.tas && course.tas.length > 0 && (
                <span className="text-xs text-slate-500 font-medium flex items-center gap-1.5 ml-2">
                  <Shield size={13} className="text-amber-500" />
                  TAs: <strong className="text-slate-700">{course.tas.join(', ')}</strong>
                </span>
              )}
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900">{course.title}</h1>
            <p className="text-sm text-slate-600 mt-2 max-w-2xl leading-relaxed">{course.description}</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 mt-8 border-b border-slate-200 overflow-x-auto pb-px">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                data-testid={`course-tab-${tab.id}`}
                className={`flex items-center gap-2 px-4 py-3 text-xs font-bold uppercase tracking-wider border-b-2 transition-all whitespace-nowrap ${
                  isActive
                    ? 'border-navy-800 text-navy-800'
                    : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                }`}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {publishMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-sm flex items-center gap-2">
          <CheckCircle2 size={18} className="text-emerald-600" />
          <span>{publishMessage}</span>
        </div>
      )}

      {/* Tab Content */}
      <div className="space-y-6">
        {/* ===================== OVERVIEW TAB ===================== */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 space-y-6">
              {/* Announcements Section */}
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                <h3 className="font-bold text-slate-900 text-base flex items-center gap-2 mb-4">
                  <Bell size={18} className="text-indigo-600" />
                  <span>Course Announcements</span>
                </h3>
                <div className="space-y-4">
                  {announcements.map((ann) => (
                    <div key={ann.id} className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                      <div className="flex items-center justify-between mb-1">
                        <h4 className="font-bold text-sm text-slate-800">{ann.title}</h4>
                        <span className="text-[11px] text-slate-400">By {ann.author_name}</span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">{ann.content}</p>
                    </div>
                  ))}
                  {announcements.length === 0 && (
                    <p className="text-xs text-slate-400 italic">No announcements posted yet.</p>
                  )}
                </div>
              </div>

              {/* Course Overview Card */}
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                <h3 className="font-bold text-slate-900 text-base mb-3">About this Course</h3>
                <p className="text-sm text-slate-600 leading-relaxed mb-4">{course.description}</p>
                <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-100 text-center">
                  <div>
                    <span className="text-xl font-bold text-slate-800">{assignments.length}</span>
                    <p className="text-xs text-slate-400 uppercase mt-0.5 font-medium">Assignments</p>
                  </div>
                  <div>
                    <span className="text-xl font-bold text-slate-800">{quizzes.length}</span>
                    <p className="text-xs text-slate-400 uppercase mt-0.5 font-medium">Quizzes</p>
                  </div>
                  <div>
                    <span className="text-xl font-bold text-slate-800">{resources.length}</span>
                    <p className="text-xs text-slate-400 uppercase mt-0.5 font-medium">Resources</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Sidebar widgets */}
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                <h3 className="font-bold text-slate-900 text-sm mb-3">Course Instructional Staff</h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm">
                      {course.teacher_name.split(' ').map(n=>n[0]).slice(0,2).join('')}
                    </div>
                    <div>
                      <p className="font-bold text-sm text-slate-800">{course.teacher_name}</p>
                      <p className="text-xs text-slate-500">Course Professor</p>
                    </div>
                  </div>
                  {course.tas && course.tas.map((taname, idx) => (
                    <div key={idx} className="flex items-center gap-3 pt-2 border-t border-slate-100">
                      <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-sm">
                        TA
                      </div>
                      <div>
                        <p className="font-bold text-sm text-slate-800">{taname}</p>
                        <p className="text-xs text-slate-500">Teaching Assistant</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ===================== ASSIGNMENTS TAB ===================== */}
        {activeTab === 'assignments' && (
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <h3 className="font-bold text-slate-800 text-base">Course Assignments</h3>
            </div>
            <div className="divide-y divide-slate-100">
              {assignments.map((a) => (
                <div key={a.id} className="p-6 hover:bg-slate-50/50 transition-colors flex items-center justify-between gap-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <h4 className="font-bold text-slate-900 text-base">{a.title}</h4>
                      {a.is_group && (
                        <span className="px-2 py-0.5 bg-purple-100 text-purple-800 rounded text-[11px] font-bold">
                          Group Assignment
                        </span>
                      )}
                      <span className="text-xs text-slate-400">· Max Grade: {a.max_grade}</span>
                    </div>
                    <p className="text-xs text-slate-600 max-w-2xl mb-2">{a.description}</p>
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <Calendar size={13} className="text-slate-400" />
                        Due: <strong>{a.due_date}</strong>
                      </span>
                      {isStudent && a.my_submission && (
                        <span>
                          Status: <StatusBadge status={a.my_submission.status} />
                        </span>
                      )}
                    </div>
                  </div>
                  <Link
                    to={`/assignments/${a.id}`}
                    data-testid={`assignment-view-btn-${a.id}`}
                    className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm shrink-0"
                  >
                    <span>{isStudent ? (a.my_submission ? 'View Submission' : 'Submit Response') : 'Review Submissions'}</span>
                    <ArrowRight size={14} />
                  </Link>
                </div>
              ))}
              {assignments.length === 0 && (
                <p className="p-8 text-center text-xs text-slate-400">No assignments created for this course.</p>
              )}
            </div>
          </div>
        )}

        {/* ===================== QUIZZES TAB ===================== */}
        {activeTab === 'quizzes' && (
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="font-bold text-slate-800 text-base">Course Quizzes & Assessments</h3>
            </div>
            <div className="divide-y divide-slate-100">
              {quizzes.map((q) => (
                <div key={q.id} className="p-6 hover:bg-slate-50/50 transition-colors flex items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-bold text-slate-900 text-base">{q.title}</h4>
                      <span className="text-xs text-slate-400">· Max Attempts: {q.max_attempts}</span>
                    </div>
                    <p className="text-xs text-slate-600 max-w-2xl mb-2">{q.description}</p>
                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                      <span>Window: <strong>{q.open_date.slice(0, 10)}</strong> to <strong>{q.close_date.slice(0, 10)}</strong></span>
                      <span>Time Limit: <strong>{q.time_limit_minutes} mins</strong></span>
                      {isStudent && (
                        <span>Attempts Remaining: <strong className={q.attempts_remaining === 0 ? 'text-red-600' : 'text-emerald-700'}>{q.attempts_remaining}</strong></span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Link
                      to={`/quizzes/${q.id}`}
                      data-testid={`quiz-view-btn-${q.id}`}
                      className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
                    >
                      <span>{isStudent ? 'Open Quiz' : 'Inspect Attempts'}</span>
                      <ArrowRight size={14} />
                    </Link>
                  </div>
                </div>
              ))}
              {quizzes.length === 0 && (
                <p className="p-8 text-center text-xs text-slate-400">No quizzes scheduled for this course.</p>
              )}
            </div>
          </div>
        )}

        {/* ===================== GRADES TAB ===================== */}
        {activeTab === 'grades' && (
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-slate-800 text-base">Course Gradebook</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {isStudent ? 'Your personal grade records.' : 'Enrolled student performance records.'}
                </p>
              </div>

              {/* Publish Final Grades Button for Professor/Admin */}
              {isProfOrAdmin && (
                <button
                  type="button"
                  onClick={handlePublishGrades}
                  disabled={publishing}
                  data-testid="publish-grades-button"
                  className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-colors self-start sm:self-auto"
                >
                  <Lock size={14} />
                  <span>{publishing ? 'Publishing...' : 'Publish & Lock Final Grades'}</span>
                </button>
              )}

              {/* TA Notice */}
              {isTA && (
                <div className="px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs font-medium">
                  TA View: You may grade submissions; final grade publication is restricted to Course Professors.
                </div>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600" data-testid="course-gradebook-table">
                <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-3 px-4">Student</th>
                    <th className="py-3 px-4">Assessments Breakdown</th>
                    <th className="py-3 px-4 text-right">Overall Percentage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {gradebookRows.map((row) => (
                    <tr key={row.student_id} className="hover:bg-slate-50/50">
                      <td className="py-3 px-4 font-bold text-slate-900 align-top">
                        {row.student_name}
                        <span className="text-xs text-slate-400 font-mono block">@{row.username}</span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-2">
                          {row.grades.map((g, idx) => (
                            <span key={idx} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 text-slate-800 text-xs border border-slate-200">
                              <span className="font-medium text-slate-600">{g.title}:</span>
                              {g.score !== null ? (
                                <strong className="text-emerald-700 font-bold">{g.score}/{g.max_score}</strong>
                              ) : (
                                <span className="text-slate-400 italic">Not graded</span>
                              )}
                              {!g.is_published && (
                                <span className="text-[10px] text-amber-700 bg-amber-100 px-1 rounded">Draft</span>
                              )}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right font-extrabold text-navy-900 text-base align-top">
                        {row.percentage}%
                      </td>
                    </tr>
                  ))}
                  {gradebookRows.length === 0 && (
                    <tr>
                      <td colSpan={3} className="py-8 text-center text-xs text-slate-400">
                        No grade records available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ===================== RESOURCES TAB ===================== */}
        {activeTab === 'resources' && (
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="font-bold text-slate-800 text-base">Course Learning Resources</h3>
            </div>
            <div className="divide-y divide-slate-100">
              {resources.map((r) => (
                <div key={r.id} className="p-6 hover:bg-slate-50/50 transition-colors flex items-center justify-between gap-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-700">
                        {r.resource_type}
                      </span>
                      {r.is_staff_only && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-100 text-red-800 border border-red-200 flex items-center gap-1">
                          <Lock size={10} /> Staff Only
                        </span>
                      )}
                      <h4 className="font-bold text-slate-900 text-base">{r.title}</h4>
                    </div>
                    <p className="text-xs text-slate-600 mb-1">{r.description}</p>
                    <span className="text-[11px] text-slate-400">Added by {r.owner_name}</span>
                  </div>
                  <a
                    href={r.url_or_content}
                    target="_blank"
                    rel="noreferrer"
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <span>Access Resource</span>
                    <ArrowRight size={13} />
                  </a>
                </div>
              ))}
              {resources.length === 0 && (
                <p className="p-8 text-center text-xs text-slate-400">No resources available.</p>
              )}
            </div>
          </div>
        )}

        {/* ===================== POLICIES TAB ===================== */}
        {activeTab === 'policies' && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <h3 className="font-bold text-slate-900 text-base mb-1">Course & Assessment Policies</h3>
              <p className="text-xs text-slate-500 mb-6">
                Official rules governing privacy, assessment submissions, grading, and academic integrity.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {policies.map((pol) => (
                  <div key={pol.id} className="p-5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-indigo-100 text-indigo-800">
                          {pol.policy_type}
                        </span>
                        <h4 className="font-bold text-sm text-slate-800">{pol.title}</h4>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">{pol.content}</p>
                    </div>
                  </div>
                ))}
                {policies.length === 0 && (
                  <p className="col-span-2 text-center text-xs text-slate-400 italic py-6">No policies configured for this course.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
