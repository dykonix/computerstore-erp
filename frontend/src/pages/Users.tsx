import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import {
  assignRole,
  createUser,
  getUserFormData,
  listUsers,
  removeRole,
  updateUser,
  updateUserLocations,
  updateUserStatus,
} from '../api/usersApi'
import type { UserCreateRequest, UserFormData, UserRecord } from '../api/usersApi'
import { useAuth } from '../auth/useAuth'

const emptyForm: UserCreateRequest = {
  username: '',
  email: '',
  mobile: '',
  employee_id: null,
  role_ids: [],
  store_ids: null,
  godown_ids: null,
  initial_password: '',
}

export default function Users() {
  const { user: currentUser, hasPermission } = useAuth()
  const [users, setUsers] = useState<UserRecord[]>([])
  const [formData, setFormData] = useState<UserFormData>({ employees: [], roles: [], stores: [], godowns: [] })
  const [form, setForm] = useState<UserCreateRequest>(emptyForm)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null)
  const [editForm, setEditForm] = useState<{ email: string; mobile: string; password: string; employee_id: number | null; role_ids: number[]; store_ids: number[]; godown_ids: number[] }>({ email: '', mobile: '', password: '', employee_id: null, role_ids: [], store_ids: [], godown_ids: [] })
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
      // Location assignments belong directly to the user and do not require an employee link.
      await createUser(form)
      // Reload both users and form data so the store/godown checkboxes reflect
      // the assignments that were just persisted by the backend.
      await reload()
      setForm(emptyForm)
      setShowCreate(false)
      setNotice('User account created with the selected role assignments.')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to create user.')
    } finally {
      setSaving(false)
    }
  }

  function startEditing(user: UserRecord) {
    setEditingUser(user)
    setEditForm({
      email: user.email,
      mobile: user.mobile,
      password: '',
      employee_id: user.employee_id,
      role_ids: [...user.role_ids],
      store_ids: [...user.store_ids],
      godown_ids: [...user.godown_ids],
    })
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
      // Location assignments are keyed directly to the user; employee linking is unrelated.
      const updatePayload: { email: string; mobile: string; password?: string; employee_id: number | null } = {
        email: editForm.email,
        mobile: editForm.mobile,
        employee_id: editForm.employee_id,
      }
      if (editForm.password.trim()) updatePayload.password = editForm.password
      await updateUser(editingUser.id, updatePayload)
      if (currentUser?.id !== editingUser.id && hasPermission('roles.manage')) {
        const originalRoleIds = new Set(editingUser.role_ids)
        const nextRoleIds = new Set(editForm.role_ids)
        for (const roleId of editForm.role_ids.filter((id) => !originalRoleIds.has(id))) {
          await assignRole(editingUser.id, roleId)
        }
        for (const roleId of editingUser.role_ids.filter((id) => !nextRoleIds.has(id))) {
          await removeRole(editingUser.id, roleId)
        }
      }
      if (hasPermission('employees.manage')) {
        await updateUserLocations(editingUser.id, {
          store_ids: editForm.store_ids,
          godown_ids: editForm.godown_ids,
        })
      }
      // Refresh both user records and user-based location assignments.
      // This prevents the next edit from showing stale store/godown selections.
      await reload()
      setEditingUser(null)
      setNotice(hasPermission('employees.manage')
        ? 'User details, role assignments and location assignments updated.'
        : 'User details and role assignments updated.')
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
          <p className="page-description">Manage tenant user accounts, roles and access assignments.</p>
        </div>
        <button className="primary-button" type="button" onClick={() => {
            if (showCreate) {
              setShowCreate(false)
              setForm(emptyForm)
              setNotice('User creation cancelled.')
            } else {
              setShowCreate(true)
              setEditingUser(null)
              setError('')
              setNotice('')
            }
          }}>
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
            <label className="form-grid__full"><span>New password (leave blank to keep current password)</span><input type="password" minLength={12} autoComplete="new-password" value={editForm.password} onChange={(event) => setEditForm({ ...editForm, password: event.target.value })} /></label>
            <label className="form-grid__full"><span>Linked employee</span><select value={editForm.employee_id ?? ''} onChange={(event) => {
              const employeeId = event.target.value ? Number(event.target.value) : null
              setEditForm({
                ...editForm,
                employee_id: employeeId,
                store_ids: employeeId === null ? [] : formData.stores.filter((store) => store.user_ids.includes(currentUser?.id ?? -1)).map((store) => store.id),
                godown_ids: employeeId === null ? [] : formData.godowns.filter((godown) => godown.user_ids.includes(currentUser?.id ?? -1)).map((godown) => godown.id),
              })
            }}><option value="">No employee linked</option>{formData.employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.name || employee.email} — {employee.email}</option>)}</select></label>
            <div className="form-grid__full">
              <span className="field-label">Role assignments</span>
              <p className="field-help">{currentUser?.id === editingUser.id ? 'You cannot change your own role assignments.' : 'Select the roles this user should have.'}</p>
              <div className="permission-list">
                {formData.roles.map((role) => (
                  <label className="permission-checkbox" key={role.id}>
                    <input type="checkbox" checked={editForm.role_ids.includes(role.id)} disabled={currentUser?.id === editingUser.id || !hasPermission('roles.manage')} onChange={(event) => setEditForm({
                      ...editForm,
                      role_ids: event.target.checked ? [...editForm.role_ids, role.id] : editForm.role_ids.filter((id) => id !== role.id),
                    })} />
                    <span><strong>{role.name}</strong></span>
                  </label>
                ))}
              </div>
            </div>
            <div className="form-grid__full">
              <span className="field-label">Store access</span>
              <p className="field-help">Store access is assigned directly to this user.</p>
              <div className="permission-list">
                {formData.stores.map((store) => (
                  <label className="permission-checkbox" key={store.id}>
                    <input type="checkbox" disabled={!hasPermission('employees.manage')} checked={editForm.store_ids.includes(store.id)} onChange={(event) => setEditForm({
                      ...editForm,
                      store_ids: event.target.checked ? [...editForm.store_ids, store.id] : editForm.store_ids.filter((id) => id !== store.id),
                    })} />
                    <span><strong>{store.name}</strong></span>
                  </label>
                ))}
              </div>
            </div>
            <div className="form-grid__full">
              <span className="field-label">Godown access</span>
              <p className="field-help">Godown access is assigned directly to this user.</p>
              <div className="permission-list">
                {formData.godowns.map((godown) => (
                  <label className="permission-checkbox" key={godown.id}>
                    <input type="checkbox" disabled={!hasPermission('employees.manage')} checked={editForm.godown_ids.includes(godown.id)} onChange={(event) => setEditForm({
                      ...editForm,
                      godown_ids: event.target.checked ? [...editForm.godown_ids, godown.id] : editForm.godown_ids.filter((id) => id !== godown.id),
                    })} />
                    <span><strong>{godown.name}</strong></span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <button className="primary-button" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
          <button className="secondary-button" type="button" onClick={() => {
            setEditingUser(null)
            setNotice('Editing cancelled. No changes were saved.')
            setError('')
          }}>Cancel</button>
        </form>
      )}

      {showCreate && (
        <form className="form-panel user-create-form" onSubmit={submitCreate}>
          <h2>Create user account</h2>
          <div className="form-grid">
            <label><span>Username</span><input required maxLength={120} value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} /></label>
            <label><span>Email</span><input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
            <label><span>Mobile</span><input required value={form.mobile} onChange={(event) => setForm({ ...form, mobile: event.target.value })} /></label>
            <label><span>Link employee (optional)</span><select value={form.employee_id ?? ''} onChange={(event) => {
              const employeeId = event.target.value ? Number(event.target.value) : null
              setForm({
                ...form,
                employee_id: employeeId,
                store_ids: employeeId === null || !hasPermission('employees.manage') ? null : formData.stores
                  .filter((store) => store.user_ids.includes(currentUser?.id ?? -1))
                  .map((store) => store.id),
                godown_ids: employeeId === null || !hasPermission('employees.manage') ? null : formData.godowns
                  .filter((godown) => godown.user_ids.includes(currentUser?.id ?? -1))
                  .map((godown) => godown.id),
              })
            }}><option value="">No employee linked</option>{formData.employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.name || employee.email} — {employee.email}</option>)}</select></label>
            {hasPermission('roles.manage') && <div className="form-grid__full">
              <span className="field-label">Assign roles (optional)</span>
              <p className="field-help">Choose one or more roles now, or leave unselected and assign roles later. Administrator access is restricted to system administrators.</p>
              <div className="permission-list">
                {formData.roles.map((role) => (
                  <label className="permission-checkbox" key={role.id}>
                    <input
                      type="checkbox"
                      checked={form.role_ids.includes(role.id)}
                      onChange={(event) => setForm({
                        ...form,
                        role_ids: event.target.checked
                          ? [...form.role_ids, role.id]
                          : form.role_ids.filter((id) => id !== role.id),
                      })}
                    />
                    <span><strong>{role.name}</strong></span>
                  </label>
                ))}
              </div>
            </div>}
            <div className="form-grid__full">
              <span className="field-label">Store access</span>
              <p className="field-help">Select the stores this user can access.</p>
              {!hasPermission('employees.manage') && (
                <p className="field-help">Your account does not have permission to change store assignments.</p>
              )}
              <div className="permission-list">
                {formData.stores.length === 0 ? (
                  <p className="field-help">No stores are available.</p>
                ) : formData.stores.map((store) => (
                  <label className="permission-checkbox" key={store.id}>
                    <input
                      type="checkbox"
                      disabled={!hasPermission('employees.manage')}
                      checked={(form.store_ids ?? []).includes(store.id)}
                      onChange={(event) => setForm({
                        ...form,
                        store_ids: event.target.checked
                          ? [...(form.store_ids ?? []), store.id]
                          : (form.store_ids ?? []).filter((id) => id !== store.id),
                      })}
                    />
                    <span><strong>{store.name}</strong></span>
                  </label>
                ))}
              </div>
            </div>
            <div className="form-grid__full">
              <span className="field-label">Godown access</span>
              <p className="field-help">Select the godowns this user can access.</p>
              {!hasPermission('employees.manage') && (
                <p className="field-help">Your account does not have permission to change godown assignments.</p>
              )}
              <div className="permission-list">
                {formData.godowns.length === 0 ? (
                  <p className="field-help">No godowns are available.</p>
                ) : formData.godowns.map((godown) => (
                  <label className="permission-checkbox" key={godown.id}>
                    <input
                      type="checkbox"
                      disabled={!hasPermission('employees.manage')}
                      checked={(form.godown_ids ?? []).includes(godown.id)}
                      onChange={(event) => setForm({
                        ...form,
                        godown_ids: event.target.checked
                          ? [...(form.godown_ids ?? []), godown.id]
                          : (form.godown_ids ?? []).filter((id) => id !== godown.id),
                      })}
                    />
                    <span><strong>{godown.name}</strong></span>
                  </label>
                ))}
              </div>
            </div>
            <label className="form-grid__full"><span>Initial password (minimum 12 characters)</span><input required minLength={12} type="password" autoComplete="new-password" value={form.initial_password} onChange={(event) => setForm({ ...form, initial_password: event.target.value })} /></label>
          </div>
          <p className="field-help">The initial password is stored as a secure hash. Share it with the user through a separate secure channel.</p>
          <button className="primary-button" type="submit" disabled={saving}>{saving ? 'Creating…' : 'Create account'}</button>
          <button className="secondary-button" type="button" disabled={saving} onClick={() => {
            setShowCreate(false)
            setForm(emptyForm)
            setError('')
            setNotice('User creation cancelled.')
          }}>Cancel</button>
        </form>
      )}

      <div className="list-toolbar">
        <label className="search-field"><span>Search users</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Username, email or role" /></label>
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
                      {hasPermission('roles.manage') && (
                        <select aria-label={`Assign or remove role for ${user.username}`} value="" disabled={currentUser?.id === user.id} onChange={(event) => void changeRole(user, event.target.value)}>
                          <option value="">Manage roles…</option>
                          {formData.roles.map((role) => <option key={role.id} value={role.id}>{user.role_ids.includes(role.id) ? `Remove: ${role.name}` : `Assign: ${role.name}`}</option>)}
                        </select>
                      )}
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
