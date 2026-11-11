import React, { useState, useEffect } from 'react';
import api from '../api';
import Breadcrumbs from '../components/Breadcrumbs';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { Users, Plus, Edit2, Shield, AlertCircle, CheckCircle } from 'lucide-react';

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Create User Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState('student');
  const [newPassword, setNewPassword] = useState('GuardSLM2026!');
  const [createError, setCreateError] = useState('');

  // Edit User Modal
  const [editingUser, setEditingUser] = useState(null);
  const [editRole, setEditRole] = useState('student');
  const [editActive, setEditActive] = useState(true);
  const [editError, setEditError] = useState('');

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await api.get('/admin/users');
      setUsers(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load user accounts.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setCreateError('');
    try {
      await api.post('/admin/users', {
        username: newUsername,
        full_name: newName,
        email: newEmail,
        role: newRole,
        password: newPassword,
      });
      setIsCreateOpen(false);
      setNewUsername('');
      setNewName('');
      setNewEmail('');
      loadUsers();
    } catch (err) {
      setCreateError(err.response?.data?.detail || 'Failed to create user account.');
    }
  };

  const handleOpenEdit = (u) => {
    setEditingUser(u);
    setEditRole(u.role);
    setEditActive(u.is_active);
    setEditError('');
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    setEditError('');
    try {
      await api.put(`/admin/users/${editingUser.id}`, {
        role: editRole,
        is_active: editActive,
      });
      setEditingUser(null);
      loadUsers();
    } catch (err) {
      setEditError(err.response?.data?.detail || 'Failed to update user.');
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
        <Breadcrumbs items={[{ to: '/admin', label: 'Admin' }, { label: 'Users' }]} />
        <button
          onClick={() => setIsCreateOpen(true)}
          data-testid="admin-create-user-btn"
          className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors"
        >
          <Plus size={16} />
          <span>Add User Account</span>
        </button>
      </div>

      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-extrabold text-slate-900">User Administration</h1>
        <p className="text-sm text-slate-500 mt-1">
          Manage system accounts, assign institutional roles, and toggle account activation.
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
          <table className="w-full text-left text-sm text-slate-600" data-testid="admin-users-table">
            <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3.5 px-6">ID</th>
                <th className="py-3.5 px-6">Full Name</th>
                <th className="py-3.5 px-6">Username</th>
                <th className="py-3.5 px-6">Email</th>
                <th className="py-3.5 px-6">Role</th>
                <th className="py-3.5 px-6">Status</th>
                <th className="py-3.5 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/50 transition-colors" data-testid={`admin-user-row-${u.username}`}>
                  <td className="py-4 px-6 font-mono text-xs text-slate-400">#{u.id}</td>
                  <td className="py-4 px-6 font-bold text-slate-900">{u.full_name}</td>
                  <td className="py-4 px-6 font-mono text-xs text-slate-600 font-semibold">@{u.username}</td>
                  <td className="py-4 px-6 text-xs text-slate-500">{u.email}</td>
                  <td className="py-4 px-6">
                    <span className="capitalize font-bold text-xs text-navy-800 bg-slate-100 px-2.5 py-1 rounded-md">
                      {u.role}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <StatusBadge status={u.is_active ? 'active' : 'inactive'} />
                  </td>
                  <td className="py-4 px-6 text-right">
                    <button
                      onClick={() => handleOpenEdit(u)}
                      data-testid={`edit-user-btn-${u.username}`}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold inline-flex items-center gap-1 transition-colors"
                    >
                      <Edit2 size={12} />
                      <span>Edit</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create User Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create New User Account"
      >
        {createError && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200">
            {createError}
          </div>
        )}
        <form onSubmit={handleCreateUser} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Username</label>
            <input
              type="text"
              required
              placeholder="e.g. student4"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              data-testid="create-user-username-input"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Full Name</label>
            <input
              type="text"
              required
              placeholder="e.g. Priya Sharma"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              data-testid="create-user-fullname-input"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Email</label>
            <input
              type="email"
              required
              placeholder="priya.sharma@guardslm.edu"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              data-testid="create-user-email-input"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Role</label>
            <select
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              data-testid="create-user-role-select"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            >
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
              <option value="admin">Administrator</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Password</label>
            <input
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              data-testid="create-user-password-input"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              data-testid="submit-create-user-btn"
              className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-lg text-xs font-semibold"
            >
              Create Account
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit User Modal */}
      <Modal
        isOpen={!!editingUser}
        onClose={() => setEditingUser(null)}
        title={`Edit User: ${editingUser?.username}`}
      >
        {editError && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200">
            {editError}
          </div>
        )}
        {editingUser && (
          <form onSubmit={handleSaveEdit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Role</label>
              <select
                value={editRole}
                onChange={(e) => setEditRole(e.target.value)}
                data-testid="edit-user-role-select"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
              >
                <option value="student">Student</option>
                <option value="teacher">Teacher</option>
                <option value="admin">Administrator</option>
              </select>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="activeStatus"
                checked={editActive}
                onChange={(e) => setEditActive(e.target.checked)}
                data-testid="edit-user-active-checkbox"
                className="w-4 h-4 text-navy-800 rounded border-slate-300 focus:ring-navy-800"
              />
              <label htmlFor="activeStatus" className="text-sm font-medium text-slate-700">
                Account Active (Can log in)
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setEditingUser(null)}
                className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                data-testid="save-edit-user-btn"
                className="px-4 py-2 bg-navy-800 hover:bg-navy-900 text-white rounded-lg text-xs font-semibold"
              >
                Save Changes
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
