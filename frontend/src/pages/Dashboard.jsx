import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import Breadcrumbs from '../components/Breadcrumbs';
import {
  BookOpen,
  ClipboardList,
  FileCheck2,
  Award,
  Users,
  Shield,
  Clock,
  ArrowRight,
  AlertCircle,
  FileText,
  CheckCircle,
  Bell,
} from 'lucide-react';

export default function Dashboard() {
  const { user, isAdmin, isTeacher, isStudent } = useAuth();
  const [courses, setCourses] = useState([]);
  const [adminStats, setAdminStats] = useState(null);
  const [recentLogs, setRecentLogs] = useState([]);
  const [myGrades, setMyGrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        // Load accessible courses
        const coursesRes = await api.get('/courses');
        setCourses(coursesRes.data);

        if (isAdmin) {
          const [statsRes, logsRes] = await Promise.all([
            api.get('/admin/stats'),
            api.get('/admin/logs?limit=5'),
          ]);
          setAdminStats(statsRes.data);
          setRecentLogs(logsRes.data);
        } else if (isStudent) {
          try {
            const gradesRes = await api.get('/grades/me');
            setMyGrades(gradesRes.data);
          } catch (e) {
            console.error("Could not fetch grades", e);
          }
        }
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load dashboard data.');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [isAdmin, isStudent]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Dashboard' }]} />

      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-navy-900 to-navy-800 rounded-2xl text-white p-6 md:p-8 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-xs font-semibold text-indigo-200 border border-white/10 mb-2">
            <span>Signed in as</span>
            <span className="capitalize font-bold text-white">{user?.role}</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">
            Welcome back, {user?.full_name}!
          </h1>
          <p className="text-slate-300 text-sm mt-1 max-w-xl">
            {isAdmin && 'Site Administrator Console. Oversee all platform courses, enrolments, and policy guards.'}
            {isTeacher && 'Faculty Dashboard. Manage course instruction, review submissions, and enter student grades.'}
            {isStudent && 'Student Learning Portal. Access enrolled courses, submit coursework, and view assessment feedback.'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/courses"
            className="px-4 py-2.5 bg-white text-navy-900 hover:bg-slate-100 rounded-xl text-sm font-semibold transition-colors flex items-center gap-2 shadow-sm"
            data-testid="dashboard-view-courses-btn"
          >
            <BookOpen size={16} />
            <span>Explore Courses</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 1. STUDENT VIEW */}
      {/* ========================================================================= */}
      {isStudent && (
        <div className="space-y-6" data-testid="student-dashboard">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <StatCard
              title="Enrolled Courses"
              value={courses.length}
              subtitle="Active curriculum registrations"
              icon={BookOpen}
              color="indigo"
            />
            <StatCard
              title="Completed Assessments"
              value={myGrades.reduce((acc, c) => acc + (c.grade_data?.items?.filter(i => i.score !== null).length || 0), 0)}
              subtitle="Graded assignments & quizzes"
              icon={CheckCircle}
              color="emerald"
            />
            <StatCard
              title="Academic Status"
              value="Good Standing"
              subtitle="All enrollment requirements met"
              icon={Award}
              color="blue"
            />
          </div>

          {/* Enrolled Courses Grid */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-slate-900">Your Enrolled Courses</h2>
              <Link to="/courses" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
                <span>View all</span>
                <ArrowRight size={14} />
              </Link>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {courses.map((course) => (
                <div
                  key={course.id}
                  className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
                  data-testid={`course-card-${course.code}`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-navy-100 text-navy-800">
                        {course.code}
                      </span>
                      <span className="text-xs text-slate-500 font-medium">Instructor: {course.teacher_name}</span>
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 mb-2">{course.title}</h3>
                    <p className="text-sm text-slate-600 line-clamp-2 mb-4">{course.description}</p>
                  </div>
                  <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-xs text-slate-500">{course.student_count} Students Enrolled</span>
                    <Link
                      to={`/courses/${course.id}`}
                      className="px-3 py-1.5 bg-navy-800 hover:bg-navy-900 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1"
                      data-testid={`enter-course-${course.code}`}
                    >
                      <span>Open Course</span>
                      <ArrowRight size={12} />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Grades Overview */}
          {myGrades.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 mb-4">Recent Academic Performance</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">Course</th>
                      <th className="py-3 px-4">Assessment Item</th>
                      <th className="py-3 px-4">Score</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Feedback</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {myGrades.flatMap(courseData =>
                      (courseData.grade_data?.items || []).map((item, idx) => (
                        <tr key={`${courseData.course_id}-${idx}`} className="hover:bg-slate-50/50">
                          <td className="py-3 px-4 font-bold text-navy-900">{courseData.course_code}</td>
                          <td className="py-3 px-4 font-medium text-slate-800">{item.title}</td>
                          <td className="py-3 px-4 font-bold">
                            {item.score !== null ? (
                              <span className="text-emerald-700">{item.score} / {item.max_score}</span>
                            ) : (
                              <span className="text-slate-400 italic">Not graded</span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            <StatusBadge status={item.status} />
                          </td>
                          <td className="py-3 px-4 text-xs text-slate-500 max-w-xs truncate">
                            {item.feedback || '—'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. TEACHER VIEW */}
      {/* ========================================================================= */}
      {isTeacher && (
        <div className="space-y-6" data-testid="teacher-dashboard">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <StatCard
              title="Assigned Courses"
              value={courses.length}
              subtitle="Courses under your instruction"
              icon={BookOpen}
              color="indigo"
            />
            <StatCard
              title="Total Students"
              value={courses.reduce((acc, c) => acc + c.student_count, 0)}
              subtitle="Enrolled across your courses"
              icon={Users}
              color="emerald"
            />
            <StatCard
              title="Active Role"
              value="Faculty Instructor"
              subtitle="Grading and curriculum authority"
              icon={Shield}
              color="blue"
            />
          </div>

          <div>
            <h2 className="text-lg font-bold text-slate-900 mb-4">Your Instruction Curriculum</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {courses.map((course) => (
                <div
                  key={course.id}
                  className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
                  data-testid={`teacher-course-card-${course.code}`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-indigo-100 text-indigo-800">
                        {course.code}
                      </span>
                      <span className="text-xs text-slate-500 font-medium">{course.student_count} Enrolled</span>
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 mb-2">{course.title}</h3>
                    <p className="text-sm text-slate-600 line-clamp-2 mb-4">{course.description}</p>
                  </div>
                  <div className="pt-4 border-t border-slate-100 flex items-center justify-between gap-2">
                    <Link
                      to={`/courses/${course.id}`}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg transition-colors"
                    >
                      Course Space
                    </Link>
                    <Link
                      to={`/grades`}
                      className="px-3 py-1.5 bg-navy-800 hover:bg-navy-900 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1"
                    >
                      <span>Gradebook</span>
                      <ArrowRight size={12} />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. ADMINISTRATOR VIEW */}
      {/* ========================================================================= */}
      {isAdmin && adminStats && (
        <div className="space-y-6" data-testid="admin-dashboard">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <StatCard
              title="Total Users"
              value={adminStats.total_users}
              subtitle={`${adminStats.total_students} Students · ${adminStats.total_teachers} Teachers`}
              icon={Users}
              color="blue"
            />
            <StatCard
              title="Active Courses"
              value={adminStats.total_courses}
              subtitle={`${adminStats.total_enrollments} Total Course Enrolments`}
              icon={BookOpen}
              color="indigo"
            />
            <StatCard
              title="Submissions"
              value={adminStats.total_submissions}
              subtitle="Student assignment records"
              icon={ClipboardList}
              color="emerald"
            />
            <StatCard
              title="Quiz Attempts"
              value={adminStats.total_quiz_attempts}
              subtitle="Automated evaluations logged"
              icon={FileCheck2}
              color="amber"
            />
          </div>

          {/* Quick Admin Actions */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900 mb-4">Site Administration Actions</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Link
                to="/admin/users"
                className="p-4 rounded-xl border border-slate-200 hover:border-indigo-500 hover:bg-indigo-50/30 transition-all flex items-center gap-3"
                data-testid="admin-quick-users"
              >
                <div className="p-2 rounded-lg bg-blue-100 text-blue-800">
                  <Users size={20} />
                </div>
                <div>
                  <h4 className="font-semibold text-slate-800 text-sm">User Directory</h4>
                  <p className="text-xs text-slate-500">Manage accounts & roles</p>
                </div>
              </Link>

              <Link
                to="/admin/enrolments"
                className="p-4 rounded-xl border border-slate-200 hover:border-indigo-500 hover:bg-indigo-50/30 transition-all flex items-center gap-3"
                data-testid="admin-quick-enrolments"
              >
                <div className="p-2 rounded-lg bg-emerald-100 text-emerald-800">
                  <BookOpen size={20} />
                </div>
                <div>
                  <h4 className="font-semibold text-slate-800 text-sm">Enrolments</h4>
                  <p className="text-xs text-slate-500">Assign students to courses</p>
                </div>
              </Link>

              <Link
                to="/admin/logs"
                className="p-4 rounded-xl border border-slate-200 hover:border-indigo-500 hover:bg-indigo-50/30 transition-all flex items-center gap-3"
                data-testid="admin-quick-logs"
              >
                <div className="p-2 rounded-lg bg-rose-100 text-rose-800">
                  <Clock size={20} />
                </div>
                <div>
                  <h4 className="font-semibold text-slate-800 text-sm">Audit Logs</h4>
                  <p className="text-xs text-slate-500">Authorization telemetry</p>
                </div>
              </Link>
            </div>
          </div>

          {/* Recent Audit Telemetry */}
          {recentLogs.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-slate-900">Recent Authorization Activity</h2>
                <Link to="/admin/logs" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
                  <span>View full log</span>
                  <ArrowRight size={14} />
                </Link>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">User</th>
                      <th className="py-3 px-4">Action</th>
                      <th className="py-3 px-4">Resource</th>
                      <th className="py-3 px-4">Decision</th>
                      <th className="py-3 px-4">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {recentLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-50/50">
                        <td className="py-3 px-4 font-medium text-slate-900">
                          {log.username} <span className="text-xs text-slate-400 capitalize">({log.role})</span>
                        </td>
                        <td className="py-3 px-4 font-mono text-xs">{log.action}</td>
                        <td className="py-3 px-4 text-xs font-mono">{log.resource_type}:{log.resource_id || '*'}</td>
                        <td className="py-3 px-4">
                          <StatusBadge status={log.outcome} />
                        </td>
                        <td className="py-3 px-4 text-xs text-slate-500 max-w-sm truncate">{log.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
