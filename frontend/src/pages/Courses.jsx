import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import Modal from '../components/Modal';
import { BookOpen, User, Plus, ArrowRight, AlertCircle } from 'lucide-react';

export default function Courses() {
  const { isAdmin } = useAuth();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Admin creation modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newCode, setNewCode] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [createError, setCreateError] = useState('');

  const loadCourses = async () => {
    try {
      setLoading(true);
      const res = await api.get('/courses');
      setCourses(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch courses.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCourses();
  }, []);

  const handleCreateCourse = async (e) => {
    e.preventDefault();
    setCreateError('');
    try {
      await api.post('/courses', {
        code: newCode,
        title: newTitle,
        description: newDesc,
      });
      setIsModalOpen(false);
      setNewCode('');
      setNewTitle('');
      setNewDesc('');
      loadCourses();
    } catch (err) {
      setCreateError(err.response?.data?.detail || 'Failed to create course.');
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
        <Breadcrumbs items={[{ label: 'Courses' }]} />
        {isAdmin && (
          <button
            onClick={() => setIsModalOpen(true)}
            data-testid="create-course-btn"
            className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors"
          >
            <Plus size={16} />
            <span>New Course</span>
          </button>
        )}
      </div>

      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-extrabold text-slate-900">Course Offerings</h1>
        <p className="text-sm text-slate-500 mt-1">
          Courses registered to your authenticated academic profile.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {courses.map((course) => (
          <div
            key={course.id}
            data-testid={`course-item-${course.code}`}
            className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 rounded-lg text-xs font-extrabold bg-navy-100 text-navy-900 border border-navy-200">
                    {course.code}
                  </span>
                  {course.current_user_role && (
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                      course.current_user_role === 'professor' ? 'bg-indigo-100 text-indigo-800 border-indigo-200' :
                      course.current_user_role === 'ta' ? 'bg-amber-100 text-amber-800 border-amber-200' :
                      course.current_user_role === 'admin' ? 'bg-red-100 text-red-800 border-red-200' :
                      'bg-emerald-100 text-emerald-800 border-emerald-200'
                    }`}>
                      {course.current_user_role}
                    </span>
                  )}
                </div>
                <span className="text-xs text-slate-500 font-medium flex items-center gap-1">
                  <User size={13} className="text-slate-400" />
                  {course.teacher_name}
                </span>
              </div>
              <h2 className="text-xl font-bold text-slate-900 mb-2">{course.title}</h2>
              <p className="text-sm text-slate-600 leading-relaxed mb-6">{course.description}</p>
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">
                {course.student_count} Students Enrolled
              </span>
              <Link
                to={`/courses/${course.id}`}
                data-testid={`enter-course-btn-${course.code}`}
                className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
              >
                <span>Enter Course</span>
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        ))}
      </div>

      {courses.length === 0 && (
        <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 p-8">
          <BookOpen size={40} className="mx-auto text-slate-300 mb-3" />
          <h3 className="text-base font-bold text-slate-800">No Courses Available</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            You are not currently enrolled in or assigned to any active courses.
          </p>
        </div>
      )}

      {/* Admin Course Creation Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create New Academic Course"
      >
        {createError && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200">
            {createError}
          </div>
        )}
        <form onSubmit={handleCreateCourse} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Course Code</label>
            <input
              type="text"
              required
              placeholder="e.g. CS201"
              value={newCode}
              onChange={(e) => setNewCode(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Course Title</label>
            <input
              type="text"
              required
              placeholder="e.g. Data Structures and Algorithms"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Description</label>
            <textarea
              rows="3"
              placeholder="Course description and learning objectives"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            ></textarea>
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
              className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-lg text-xs font-semibold"
            >
              Save Course
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
