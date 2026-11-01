import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import {
  assignRole,
  createUser,
  getUserFormData,
  listUsers,
  removeRole,
  updateUser,
  updateUserStatus,
} from '../api/usersApi'
import type { UserCreateRequest, UserFormData, UserRecord } from '../api/usersApi'
import { useAuth } from '../auth/useAuth'

const emptyForm: UserCreateRequest = {
  username: '',
  email: '',
  mobile: '',
  employee_id: null,
  initial_password: '',
}

export default function Users() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<UserRecord[]>([])
  const [formData, setFormData] = useState<UserFormData>({ employees: [], roles: [] })
  const [form, setForm] = useState<UserCreateRequest>(emptyForm)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null)
  const [editForm, setEditForm] = useState<{ email: string; mobile: string; employee_id: number | null }>({ email: '', mobile: '', employee_id: null })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function reload() {
    setLoading(true)
    try {
      const [userRows, options] = await Promise.all([listUsers(), getUserFormData()])
      setUsers(userRows)
      setFormData(options)
      setError('')
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load users.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void reload()
  }, [])

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return users
    return users.filter((user) =>
      [user.username, user.email, user.mobile, user.employee_name ?? '', ...user.role_names]
        .some((value) => value.toLowerCase().includes(query)),
    )
  }, [users, search])

  async function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const created = await createUser(form)
      setUsers((current) => [...current, created].sort((a, b) => a.username.localeCompare(b.username)))
      setForm(emptyForm)
      setShowCreate(false)
      setNotice('User account created. Assign a role below to grant access.')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to create user.')
    } finally {
      setSaving(false)
    }
  }

  function startEditing(user: UserRecord) {
    setEditingUser(user)
    setEditForm({ email: user.email, mobile: user.mobile, employee_id: user.employee_id })
    setShowCreate(false)
    setError('')
    setNotice('')
  }

  async function submitEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingUser) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const updated = await updateUser(editingUser.id, editForm)
      setUsers((current) => current.map((item) => item.id === updated.id ? updated : item))
      setEditingUser(null)
      setNotice('User details updated.')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to update user details.')
    } finally {
      setSaving(false)
    }
  }

  async function toggleStatus(user: UserRecord) {
    setError('')
    setNotice('')
    try {
      const updated = await updateUserStatus(user.id, !user.is_active)
      setUsers((current) => current.map((item) => item.id === user.id ? updated : item))
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to update account status.')
    }
  }

  async function changeRole(user: UserRecord, roleIdValue: string) {
    if (!roleIdValue) return
    const roleId = Number(roleIdValue)
    const alreadyAssigned = user.role_ids.includes(roleId)
    setError('')
    setNotice('')
    try {
      if (alreadyAssigned) {
        await removeRole(user.id, roleId)
      } else {
        await assignRole(user.id, roleId)
      }
      await reload()
      setNotice('Role assignment updated.')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to update role assignment.')
    }
  }

  return (
    <section className="page-section">
      <div className="page-title-row">
        <div>
          <h1>Users</h1>
          <p className="page-description">Manage sign-in accounts, employee links and role assignments.</p>
        </div>
        <button className="primary-button" type="button" onClick={() => { setShowCreate((value) => !value); setError(''); setNotice('') }}>
          {showCreate ? 'Cancel' : 'Create user'}
        </button>
      </div>

      {error && <div className="notice notice--error" role="alert">{error}</div>}
      {notice && <div className="notice notice--success" role="status">{notice}</div>}

      {editingUser && (
        <form className="form-panel user-create-form" onSubmit={submitEdit}>
          <h2>Edit account: {editingUser.username}</h2>
          <div className="form-grid">
            <label><span>Email</span><input required type="email" value={editForm.email} onChange={(event) => setEditForm({ ...editForm, email: event.target.value })} /></label>
            <label><span>Mobile</span><input required value={editForm.mobile} onChange={(event) => setEditForm({ ...editForm, mobile: event.target.value })} /></label>
            <label className="form-grid__full"><span>Linked employee</span><select value={editForm.employee_id ?? ''} onChange={(event) => setEditForm({ ...editForm, employee_id: event.target.value ? Number(event.target.value) : null })}><option value="">No employee linked</option>{formData.employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.name || employee.email} — {employee.email}</option>)}</select></label>
          </div>
          <button className="primary-button" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
          <button className="secondary-button" type="button" onClick={() => setEditingUser(null)}>Cancel</button>
        </form>
      )}

      {showCreate && (
        <form className="form-panel user-create-form" onSubmit={submitCreate}>
          <h2>Create user account</h2>
          <div className="form-grid">
            <label><span>Username</span><input required maxLength={120} value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} /></label>
            <label><span>Email</span><input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
            <label><span>Mobile</span><input required value={form.mobile} onChange={(event) => setForm({ ...form, mobile: event.target.value })} /></label>
            <label><span>Link employee (optional)</span><select value={form.employee_id ?? ''} onChange={(event) => setForm({ ...form, employee_id: event.target.value ? Number(event.target.value) : null })}><option value="">No employee linked</option>{formData.employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.name || employee.email} — {employee.email}</option>)}</select></label>
            <label className="form-grid__full"><span>Initial password (minimum 12 characters)</span><input required minLength={12} type="password" autoComplete="new-password" value={form.initial_password} onChange={(event) => setForm({ ...form, initial_password: event.target.value })} /></label>
          </div>
          <p className="field-help">The initial password is stored as a secure hash. Share it with the user through a separate secure channel.</p>
          <button className="primary-button" type="submit" disabled={saving}>{saving ? 'Creating…' : 'Create account'}</button>
        </form>
      )}

      <div className="list-toolbar">
        <label className="search-field"><span>Search users</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Username, email, employee or role" /></label>
        <span className="result-count">{filteredUsers.length} users</span>
      </div>

      {loading ? <div className="loading-panel">Loading users…</div> : filteredUsers.length === 0 ? (
        <div className="empty-state">No user accounts found.</div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead><tr><th>User</th><th>Employee</th><th>Roles</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {filteredUsers.map((user) => (
                <tr key={user.id}>
                  <td><strong>{user.username}</strong><span className="table-subtext">{user.email}</span><span className="table-subtext">{user.mobile}</span></td>
                  <td>{user.employee_name || 'Not linked'}</td>
                  <td>
                    <div className="role-assignment">
                      {user.role_names.length ? user.role_names.map((roleName) => <span className="role-chip" key={roleName}>{roleName}</span>) : <span className="table-subtext">No roles assigned</span>}
                      <select aria-label={`Assign or remove role for ${user.username}`} value="" disabled={currentUser?.id === user.id} onChange={(event) => void changeRole(user, event.target.value)}>
                        <option value="">Manage roles…</option>
                        {formData.roles.map((role) => <option key={role.id} value={role.id}>{user.role_ids.includes(role.id) ? `Remove: ${role.name}` : `Assign: ${role.name}`}</option>)}
                      </select>
                    </div>
                  </td>
                  <td><span className={user.is_active ? 'status-pill status-pill--active' : 'status-pill'}>{user.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td><button className="secondary-button" type="button" onClick={() => startEditing(user)}>Edit</button><button className="secondary-button" type="button" onClick={() => void toggleStatus(user)}>{user.is_active ? 'Deactivate' : 'Activate'}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
