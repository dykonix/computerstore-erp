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
  const [editForm, setEditForm] = useState<{ email: string; mobile: string; employee_id: number | null; role_ids: number[]; store_ids: number[]; godown_ids: number[] }>({ email: '', mobile: '', employee_id: null, role_ids: [], store_ids: [], godown_ids: [] })
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
      if (form.employee_id === null && ((form.store_ids ?? []).length || (form.godown_ids ?? []).length)) {
        setError('Link an employee before saving store or godown assignments.')
        return
      }
      const created = await createUser(form)
      setUsers((current) => [...current, created].sort((a, b) => a.username.localeCompare(b.username)))
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
      employee_id: user.employee_id,
      role_ids: [...user.role_ids],
      store_ids: user.employee_id === null ? [] : formData.stores.filter((store) => store.employee_ids.includes(user.employee_id!)).map((store) => store.id),
      godown_ids: user.employee_id === null ? [] : formData.godowns.filter((godown) => godown.employee_ids.includes(user.employee_id!)).map((godown) => godown.id),
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
      if (editForm.employee_id === null && (editForm.store_ids.length || editForm.godown_ids.length)) {
        setError('Link an employee before assigning stores or godowns.')
        return
      }
      const updated = await updateUser(editingUser.id, {
        email: editForm.email,
        mobile: editForm.mobile,
        employee_id: editForm.employee_id,
      })
      if (currentUser?.id !== editingUser.id) {
        const originalRoleIds = new Set(editingUser.role_ids)
        const nextRoleIds = new Set(editForm.role_ids)
        for (const roleId of editForm.role_ids.filter((id) => !originalRoleIds.has(id))) {
          await assignRole(editingUser.id, roleId)
        }
        for (const roleId of editingUser.role_ids.filter((id) => !nextRoleIds.has(id))) {
          await removeRole(editingUser.id, roleId)
        }
      }
      if (editForm.employee_id !== null) {
        await updateUserLocations(editingUser.id, {
          store_ids: editForm.store_ids,
          godown_ids: editForm.godown_ids,
        })
      }
      const refreshedUsers = await listUsers()
      setUsers(refreshedUsers)
      setEditingUser(null)
      setNotice('User details, role assignments and location assignments updated.')
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
            <label className="form-grid__full"><span>Linked employee</span><select value={editForm.employee_id ?? ''} onChange={(event) => {
              const employeeId = event.target.value ? Number(event.target.value) : null
              setEditForm({
                ...editForm,
                employee_id: employeeId,
                store_ids: employeeId === null ? [] : formData.stores.filter((store) => store.employee_ids.includes(employeeId)).map((store) => store.id),
                godown_ids: employeeId === null ? [] : formData.godowns.filter((godown) => godown.employee_ids.includes(employeeId)).map((godown) => godown.id),
              })
            }}><option value="">No employee linked</option>{formData.employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.name || employee.email} — {employee.email}</option>)}</select></label>
            <div className="form-grid__full">
              <span className="field-label">Role assignments</span>
              <p className="field-help">{currentUser?.id === editingUser.id ? 'You cannot change your own role assignments.' : 'Select the roles this user should have.'}</p>
              <div className="permission-list">
                {formData.roles.map((role) => (
                  <label className="permission-checkbox" key={role.id}>
                    <input type="checkbox" checked={editForm.role_ids.includes(role.id)} disabled={currentUser?.id === editingUser.id} onChange={(event) => setEditForm({
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
              <p className="field-help">Assignments are saved to the linked employee. Choose an employee to load their current store assignments.</p>
              <div className="permission-list">
                {formData.stores.map((store) => (
                  <label className="permission-checkbox" key={store.id}>
                    <input type="checkbox" checked={editForm.store_ids.includes(store.id)} onChange={(event) => setEditForm({
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
              <p className="field-help">Assignments are saved to the linked employee. Choose an employee to load their current godown assignments.</p>
              <div className="permission-list">
                {formData.godowns.map((godown) => (
                  <label className="permission-checkbox" key={godown.id}>
                    <input type="checkbox" checked={editForm.godown_ids.includes(godown.id)} onChange={(event) => setEditForm({
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
            <label><span>Link employee (optional)</span><select value={form.employee_id ?? ''} onChange={(event) => {
              const employeeId = event.target.value ? Number(event.target.value) : null
              setForm({
                ...form,
                employee_id: employeeId,
                store_ids: employeeId === null || !hasPermission('employees.manage') ? null : formData.stores
                  .filter((store) => store.employee_ids.includes(employeeId))
                  .map((store) => store.id),
                godown_ids: employeeId === null || !hasPermission('employees.manage') ? null : formData.godowns
                  .filter((godown) => godown.employee_ids.includes(employeeId))
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
              <p className="field-help">Store-scoped permissions use the linked employee's store assignments. Selecting stores here sets that employee's assigned stores. Existing assignments are preselected.</p>
              <p className="field-help">Select stores here. To save non-empty assignments, link an employee first. Checkboxes remain available regardless of employee selection.</p>
              <div className="permission-list">
                {formData.stores.map((store) => (
                  <label className="permission-checkbox" key={store.id}>
                    <input
                      type="checkbox"
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
              <p className="field-help">Inventory location permissions can be limited to the godowns assigned to this employee. Selecting godowns here updates the employee's godown assignments.</p>
              <p className="field-help">Select godowns here. To save non-empty assignments, link an employee first. Checkboxes remain available regardless of employee selection.</p>
              <div className="permission-list">
                {formData.godowns.map((godown) => (
                  <label className="permission-checkbox" key={godown.id}>
                    <input
                      type="checkbox"
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
