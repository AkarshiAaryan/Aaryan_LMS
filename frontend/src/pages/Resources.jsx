import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import Modal from '../components/Modal';
import { FolderOpen, FileText, Download, Plus, ArrowRight, AlertCircle, Trash2, Eye, Lock, ExternalLink } from 'lucide-react';

export default function Resources() {
  const { user, isTeacher, isAdmin } = useAuth();
  const [courses, setCourses] = useState([]);
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Add resource modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCourseId, setSelectedCourseId] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [resourceType, setResourceType] = useState('document');
  const [urlOrContent, setUrlOrContent] = useState('');
  const [modalError, setModalError] = useState('');
  const [viewingResource, setViewingResource] = useState(null);

  const handleDownloadResource = async (resource) => {
    try {
      const res = await api.get(`/resources/${resource.id}/download`, { responseType: 'blob' });
      const blobUrl = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = blobUrl;
      const cleanName = resource.title.replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase();
      const ext = resource.url_or_content?.includes('.pdf') ? 'pdf' : 'txt';
      link.setAttribute('download', `${cleanName}.${ext}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error('Download error:', err);
      alert(err.response?.data?.detail || 'Failed to download resource.');
    }
  };

  const loadAllResources = async () => {
    try {
      setLoading(true);
      const coursesRes = await api.get('/courses');
      setCourses(coursesRes.data);
      if (coursesRes.data.length > 0 && !selectedCourseId) {
        setSelectedCourseId(String(coursesRes.data[0].id));
      }

      const allRes = [];
      for (const c of coursesRes.data) {
        try {
          const res = await api.get(`/courses/${c.id}/resources`);
          allRes.push(...res.data);
        } catch (e) {
          console.error(`Error loading resources for course ${c.code}`, e);
        }
      }
      setResources(allRes);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch course resources.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllResources();
  }, []);

  const handleAddResource = async (e) => {
    e.preventDefault();
    setModalError('');

    try {
      await api.post(`/courses/${selectedCourseId}/resources`, {
        title,
        description,
        resource_type: resourceType,
        url_or_content: urlOrContent || 'https://resources.guardslm.edu/files/resource.pdf',
        is_visible: true,
      });
      setIsModalOpen(false);
      setTitle('');
      setDescription('');
      setUrlOrContent('');
      loadAllResources();
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to create resource.');
    }
  };

  const handleDeleteResource = async (resId) => {
    if (!window.confirm('Are you sure you want to delete this resource?')) return;
    try {
      await api.delete(`/resources/${resId}`);
      loadAllResources();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete resource.');
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
        <Breadcrumbs items={[{ label: 'Resources' }]} />
        {(isTeacher || isAdmin) && (
          <button
            onClick={() => setIsModalOpen(true)}
            data-testid="add-resource-btn"
            className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors"
          >
            <Plus size={16} />
            <span>Add Resource</span>
          </button>
        )}
      </div>

      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-extrabold text-slate-900">Learning Materials & Resources</h1>
        <p className="text-sm text-slate-500 mt-1">
          Lecture slides, supplementary reading packs, and course documentation.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5" data-testid="resources-grid">
        {resources.map((r) => (
          <div
            key={r.id}
            data-testid={`resource-card-${r.id}`}
            className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="px-2.5 py-0.5 rounded text-xs font-extrabold bg-navy-100 text-navy-800">
                  {r.course_code}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-700">
                  {r.resource_type}
                </span>
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-1.5">{r.title}</h3>
              <p className="text-xs text-slate-600 leading-relaxed mb-4">{r.description}</p>
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">Owner: {r.owner_name}</span>
              <div className="flex items-center gap-2">
                {(isAdmin || isTeacher) && (
                  <button
                    onClick={() => handleDeleteResource(r.id)}
                    className="p-1.5 text-slate-400 hover:text-red-600 transition-colors"
                    title="Delete Resource"
                    data-testid={`delete-resource-btn-${r.id}`}
                  >
                    <Trash2 size={15} />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setViewingResource(r)}
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors"
                >
                  <Eye size={13} />
                  <span>View</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDownloadResource(r)}
                  data-testid={`download-resource-btn-${r.id}`}
                  className="px-3.5 py-1.5 bg-navy-800 hover:bg-navy-900 text-white rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors shadow-sm"
                >
                  <Download size={13} />
                  <span>Download</span>
                </button>
              </div>
            </div>
          </div>
        ))}
        {resources.length === 0 && (
          <div className="col-span-2 py-12 text-center text-slate-400 text-xs italic bg-white rounded-2xl border border-slate-200 p-8">
            No course resources available for your account.
          </div>
        )}
      </div>

      {/* Add Resource Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Upload / Add Learning Resource"
      >
        {modalError && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200">
            {modalError}
          </div>
        )}
        <form onSubmit={handleAddResource} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Course</label>
            <select
              value={selectedCourseId}
              onChange={(e) => setSelectedCourseId(e.target.value)}
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
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Resource Title</label>
            <input
              type="text"
              required
              placeholder="e.g. Week 2 Lecture Notes"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Resource Type</label>
            <select
              value={resourceType}
              onChange={(e) => setResourceType(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            >
              <option value="document">Document / PDF</option>
              <option value="slides">Lecture Slides</option>
              <option value="link">Web Reference / Link</option>
              <option value="code">Source Code / Repo</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Description</label>
            <textarea
              rows="2"
              placeholder="Summary of resource contents"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            ></textarea>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">URL or File Path</label>
            <input
              type="text"
              placeholder="https://resources.guardslm.edu/..."
              value={urlOrContent}
              onChange={(e) => setUrlOrContent(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800 font-mono text-xs"
            />
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
              Publish Resource
            </button>
          </div>
        </form>
      </Modal>

      {/* Resource Document Viewer Modal */}
      <Modal
        isOpen={Boolean(viewingResource)}
        onClose={() => setViewingResource(null)}
        title={viewingResource?.title || 'Resource Document Viewer'}
        maxWidth="max-w-2xl"
      >
        {viewingResource && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-0.5 rounded text-xs font-extrabold bg-navy-100 text-navy-800">
                {viewingResource.course_code}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-700">
                {viewingResource.resource_type}
              </span>
              {viewingResource.is_staff_only && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-100 text-red-800 border border-red-200 flex items-center gap-1">
                  <Lock size={10} /> Staff Only
                </span>
              )}
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Description</p>
              <p className="text-sm text-slate-800 leading-relaxed">{viewingResource.description}</p>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-800 space-y-1">
              <p className="font-semibold flex items-center gap-1">
                <span>Simulated Academic Benchmark Resource</span>
              </p>
              <p className="text-amber-700 leading-relaxed text-[11px]">
                In the GuardSLM research environment, external documents are indexed with synthetic domain URIs (e.g., <code className="bg-amber-100 px-1 py-0.5 rounded font-mono text-[11px]">{viewingResource.url_or_content}</code>). Click <strong>Download Document</strong> below to retrieve the complete simulated file payload.
              </p>
            </div>

            <div className="bg-slate-900 text-slate-100 rounded-xl p-4 font-mono text-xs overflow-x-auto max-h-56 space-y-2 border border-slate-800">
              <div className="text-emerald-400 font-bold border-b border-slate-700 pb-2">
                === {viewingResource.title} ===
              </div>
              <p className="text-slate-300"><span className="text-slate-500">Course:</span> {viewingResource.course_code}</p>
              <p className="text-slate-300"><span className="text-slate-500">Instructor:</span> {viewingResource.owner_name}</p>
              <p className="text-slate-300"><span className="text-slate-500">Format:</span> {viewingResource.resource_type.toUpperCase()}</p>
              <div className="pt-2 text-slate-400 text-[11px] border-t border-slate-800">
                [DOCUMENT STRUCTURE & NOTES]<br />
                • Section 1: Overview, Learning Outcomes & Core Terminology<br />
                • Section 2: Methodological Foundations & Structural Diagrams<br />
                • Section 3: Recommended Readings, Reference Tables & Sample Problems
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <span className="text-xs text-slate-400 font-mono truncate max-w-xs" title={viewingResource.url_or_content}>
                {viewingResource.url_or_content}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleDownloadResource(viewingResource)}
                  className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
                >
                  <Download size={14} />
                  <span>Download Document</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewingResource(null)}
                  className="px-4 py-2 border border-slate-200 text-slate-700 hover:bg-slate-50 rounded-xl text-xs font-semibold transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
