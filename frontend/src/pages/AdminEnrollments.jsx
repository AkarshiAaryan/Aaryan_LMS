import React, { useState, useEffect } from 'react';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import Modal from '../components/Modal';
import { Layers, Plus, Trash2, AlertCircle, BookOpen, User } from 'lucide-react';

export default function AdminEnrollments() {
  const [enrollments, setEnrollments] = useState([]);
  const [courses, setCourses] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Add Enrolment Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCourseId, setSelectedCourseId] = useState('');
  const [selectedUserId, setSelectedUserId] = useState('');
  const [modalError, setModalError] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [enrRes, coursesRes, usersRes] = await Promise.all([
        api.get('/admin/enrolments'),
        api.get('/courses'),
        api.get('/admin/users'),
      ]);
      setEnrollments(enrRes.data);
      setCourses(coursesRes.data);
      const studentUsers = usersRes.data.filter((u) => u.role === 'student');
      setUsers(studentUsers);

      if (coursesRes.data.length > 0) setSelectedCourseId(String(coursesRes.data[0].id));
      if (studentUsers.length > 0) setSelectedUserId(String(studentUsers[0].id));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load enrolment records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateEnrollment = async (e) => {
    e.preventDefault();
    setModalError('');
    try {
      await api.post('/admin/enrolments', {
        course_id: parseInt(selectedCourseId, 10),
        user_id: parseInt(selectedUserId, 10),
        role: 'student',
      });
      setIsModalOpen(false);
      loadData();
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to enrol student in course.');
    }
  };

  const handleDeleteEnrollment = async (enrId) => {
    if (!window.confirm('Are you sure you want to remove this enrolment?')) return;
    try {
      await api.delete(`/admin/enrolments/${enrId}`);
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to remove enrolment.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Breadcrumbs items={[{ to: '/admin', label: 'Admin' }, { label: 'Enrolments' }]} />
        <button
          onClick={() => setIsModalOpen(true)}
          data-testid="admin-add-enrolment-btn"
          className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors"
        >
          <Plus size={16} />
          <span>Enrol Student</span>
        </button>
      </div>

      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-extrabold text-slate-900">Course Enrolment Roster</h1>
        <p className="text-sm text-slate-500 mt-1">
          Control which student accounts may access each academic course fixture.
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
          <table className="w-full text-left text-sm text-slate-600" data-testid="admin-enrolments-table">
            <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3.5 px-6">ID</th>
                <th className="py-3.5 px-6">Course</th>
                <th className="py-3.5 px-6">Student</th>
                <th className="py-3.5 px-6">Enrolled Role</th>
                <th className="py-3.5 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {enrollments.map((enr) => (
                <tr key={enr.id} className="hover:bg-slate-50/50 transition-colors" data-testid={`enrolment-row-${enr.id}`}>
                  <td className="py-4 px-6 font-mono text-xs text-slate-400">#{enr.id}</td>
                  <td className="py-4 px-6 font-bold text-slate-900">
                    <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-navy-100 text-navy-800 mr-2">
                      {enr.course_code}
                    </span>
                    <span>{enr.course_title}</span>
                  </td>
                  <td className="py-4 px-6 font-medium text-slate-800">
                    {enr.full_name}
                    <span className="text-xs text-slate-400 font-mono block">@{enr.username}</span>
                  </td>
                  <td className="py-4 px-6 capitalize text-xs text-slate-600 font-semibold">
                    {enr.role}
                  </td>
                  <td className="py-4 px-6 text-right">
                    <button
                      onClick={() => handleDeleteEnrollment(enr.id)}
                      data-testid={`unenrol-btn-${enr.id}`}
                      className="p-1.5 text-slate-400 hover:text-red-600 transition-colors"
                      title="Unenrol student"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {enrollments.length === 0 && (
                <tr>
                  <td colSpan="5" className="py-12 text-center text-slate-400 text-xs italic">
                    No enrolments found in database.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Enrolment Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Enrol Student into Course"
      >
        {modalError && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200">
            {modalError}
          </div>
        )}
        <form onSubmit={handleCreateEnrollment} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Target Course</label>
            <select
              value={selectedCourseId}
              onChange={(e) => setSelectedCourseId(e.target.value)}
              data-testid="enrol-course-select"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            >
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} — {c.title}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Student Account</label>
            <select
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value)}
              data-testid="enrol-student-select"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            >
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} (@{u.username})
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              data-testid="submit-enrolment-btn"
              className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-lg text-xs font-semibold"
            >
              Confirm Enrolment
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
