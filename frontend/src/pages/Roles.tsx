import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import {
  createRole,
  getRoleFormData,
  listRoles,
  replaceRolePermissions,
  updateRole,
} from '../api/rolesApi'
import type {
  PermissionScope,
  RoleFormData,
  RoleRecord,
} from '../api/rolesApi'

const emptyRole = { name: '', description: '' }
const storeScopedPermissions = new Set(['sell'])
const locationScopedPermissions = new Set(['inventory.view', 'inventory.manage'])
type RoleForm = { name: string; description: string; is_active: boolean }

export default function Roles() {
  const [roles, setRoles] = useState<RoleRecord[]>([])
  const [formData, setFormData] = useState<RoleFormData>({
    permissions: [],
    can_manage_permissions: false,
  })
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editingRole, setEditingRole] = useState<RoleRecord | null>(null)
  const [roleForm, setRoleForm] = useState<RoleForm>({ ...emptyRole, is_active: true })
  const [permissionRole, setPermissionRole] = useState<RoleRecord | null>(null)
  const [grants, setGrants] = useState<Record<string, PermissionScope>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function reload() {
    setLoading(true)
    try {
      const [roleRows, options] = await Promise.all([listRoles(), getRoleFormData()])
      setRoles(roleRows)
      setFormData(options)
      setError('')
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load roles.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void reload()
  }, [])

  const filteredRoles = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return roles
    return roles.filter((role) =>
      [role.name, role.description ?? '', ...role.permissions.map((grant) => grant.permission_code)]
        .some((value) => value.toLowerCase().includes(query)),
    )
  }, [roles, search])

  function startEditing(role: RoleRecord) {
    setEditingRole(role)
    setRoleForm({
      name: role.name,
      description: role.description ?? '',
      is_active: role.is_active,
    })
    setPermissionRole(null)
    setShowCreate(false)
    setError('')
    setNotice('')
  }

  function startPermissionEdit(role: RoleRecord) {
    setPermissionRole(role)
    setGrants(Object.fromEntries(
      role.permissions
        .filter((grant) => grant.permission_code !== 'ALL')
        .map((grant) => [grant.permission_code, grant.scope]),
    ))
    setEditingRole(null)
    setShowCreate(false)
    setError('')
    setNotice('')
  }

  async function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const created = await createRole({
        name: roleForm.name,
        description: roleForm.description.trim() || null,
      })
      await reload()
      setShowCreate(false)
      setRoleForm({ ...emptyRole, is_active: true })
      setNotice(`Role “${created.name}” created. Configure its permissions next.`)
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to create role.')
    } finally {
      setSaving(false)
    }
  }

  async function submitRoleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingRole) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await updateRole(editingRole.id, {
        name: roleForm.name,
        description: roleForm.description.trim() || null,
        is_active: roleForm.is_active,
      })
      await reload()
      setEditingRole(null)
      setNotice('Role details updated.')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to update role.')
    } finally {
      setSaving(false)
    }
  }

  async function submitPermissions(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!permissionRole) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await replaceRolePermissions(
        permissionRole.id,
        Object.entries(grants).map(([permission_code, scope]) => ({
          permission_code,
          scope,
        })),
      )
      await reload()
      setPermissionRole(null)
      setNotice('Role permissions updated.')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Unable to update role permissions.')
    } finally {
      setSaving(false)
    }
  }

  function isSystemAdministrator(role: RoleRecord) {
    return role.permissions.some((grant) => grant.permission_code === 'ALL')
  }

  return (
    <section className="page-section">
      <div className="page-title-row">
        <div>
          <h1>Roles &amp; Permissions</h1>
          <p className="page-description">Define role-based access for employees. Permissions are enforced by the backend, not just hidden in the interface.</p>
        </div>
        <button className="primary-button" type="button" onClick={() => { setShowCreate((value) => !value); setEditingRole(null); setPermissionRole(null); setError(''); setNotice('') }}>
          {showCreate ? 'Cancel' : 'Create role'}
        </button>
      </div>

      {error && <div className="notice notice--error" role="alert">{error}</div>}
      {notice && <div className="notice notice--success" role="status">{notice}</div>}

      {showCreate && (
        <form className="form-panel user-create-form" onSubmit={submitCreate}>
          <h2>Create role</h2>
          <div className="form-grid">
            <label><span>Role name</span><input required maxLength={120} value={roleForm.name} onChange={(event) => setRoleForm({ ...roleForm, name: event.target.value })} /></label>
            <label><span>Description (optional)</span><input maxLength={500} value={roleForm.description} onChange={(event) => setRoleForm({ ...roleForm, description: event.target.value })} /></label>
          </div>
          <button className="primary-button" type="submit" disabled={saving}>{saving ? 'Creating…' : 'Create role'}</button>
        </form>
      )}

      {editingRole && (
        <form className="form-panel user-create-form" onSubmit={submitRoleUpdate}>
          <h2>Edit role: {editingRole.name}</h2>
          <div className="form-grid">
            <label><span>Role name</span><input required maxLength={120} value={roleForm.name} onChange={(event) => setRoleForm({ ...roleForm, name: event.target.value })} /></label>
            <label><span>Description (optional)</span><input maxLength={500} value={roleForm.description} onChange={(event) => setRoleForm({ ...roleForm, description: event.target.value })} /></label>
            <label className="role-active-toggle"><span>Role active</span><input type="checkbox" checked={roleForm.is_active} disabled={isSystemAdministrator(editingRole)} onChange={(event) => setRoleForm({ ...roleForm, is_active: event.target.checked })} /></label>
          </div>
          {isSystemAdministrator(editingRole) && <p className="field-help">The system administrator role is protected and cannot be deactivated or have its permissions changed.</p>}
          <button className="primary-button" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
          <button className="secondary-button" type="button" onClick={() => setEditingRole(null)}>Cancel</button>
        </form>
      )}

      {permissionRole && (
        <form className="form-panel role-permissions-form" onSubmit={submitPermissions}>
          <div className="section-heading">
            <div><h2>Permissions: {permissionRole.name}</h2><p className="page-description">Select the permissions this role should grant. Saving replaces the role's current permission set.</p></div>
          </div>
          <div className="permission-list">
            {formData.permissions.map((permission) => {
              const checked = permission.code in grants
              return (
                <div className="permission-row" key={permission.code}>
                  <label className="permission-checkbox">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(event) => {
                        setGrants((current) => {
                          const next = { ...current }
                          if (event.target.checked) next[permission.code] = 'assigned_stores'
                          else delete next[permission.code]
                          return next
                        })
                      }}
                    />
                    <span><strong>{permission.code}</strong>{permission.description && <small>{permission.description}</small>}</span>
                  </label>
                  {checked && (storeScopedPermissions.has(permission.code) || locationScopedPermissions.has(permission.code)) && (
                    <label className="permission-scope">
                      <span>{locationScopedPermissions.has(permission.code) ? "Inventory location scope" : "Store scope"}</span>
                      <select
                        value={grants[permission.code]}
                        onChange={(event) => setGrants((current) => ({ ...current, [permission.code]: event.target.value as PermissionScope }))}
                      >
                        {locationScopedPermissions.has(permission.code) ? <>
                          <option value="assigned_locations">Assigned stores and godowns</option>
                          <option value="all_tenant_locations">All company locations</option>
                        </> : <>
                          <option value="assigned_stores">Assigned stores</option>
                          <option value="all_tenant_stores">All company stores</option>
                        </>}
                      </select>
                    </label>
                  )}
                </div>
              )
            })}
          </div>
          <div className="form-actions">
            <button className="secondary-button" type="button" onClick={() => setPermissionRole(null)}>Cancel</button>
            <button className="primary-button" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save permissions'}</button>
          </div>
        </form>
      )}

      <div className="list-toolbar">
        <label className="search-field"><span>Search roles</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Role name, description or permission" /></label>
        <span className="result-count">{filteredRoles.length} roles</span>
      </div>

      {loading ? <div className="loading-panel">Loading roles…</div> : filteredRoles.length === 0 ? (
        <div className="empty-state">No roles found.</div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead><tr><th>Role</th><th>Permissions</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {filteredRoles.map((role) => {
                const systemRole = isSystemAdministrator(role)
                return (
                  <tr key={role.id}>
                    <td><strong>{role.name}</strong><span className="table-subtext">{role.description || 'No description'}</span></td>
                    <td><div className="role-permission-chips">{role.permissions.map((grant) => <span className="role-chip" key={grant.permission_code}>{grant.permission_code}</span>)}</div></td>
                    <td><span className={role.is_active ? 'status-pill status-pill--active' : 'status-pill'}>{role.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td className="role-actions">
                      <button className="secondary-button" type="button" onClick={() => startEditing(role)}>Edit</button>
                      {formData.can_manage_permissions && !systemRole && <button className="secondary-button" type="button" onClick={() => startPermissionEdit(role)}>Permissions</button>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
