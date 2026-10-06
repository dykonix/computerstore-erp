import { useEffect, useState } from 'react'
import {
  createCategory,
  fetchCategories,
  fetchCategory,
  setCategoryStatus,
  updateCategory,
} from '../api/categoryApi'
import type { Category, CategoryWriteRequest } from '../api/categoryApi'
import CategoryForm from '../components/CategoryForm'
import CategoryList from '../components/CategoryList'

export default function CategoryMaster() {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [listLoading, setListLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null)
  const [statusUpdatingId, setStatusUpdatingId] = useState<number | null>(null)

  async function loadCategories() {
    setListLoading(true)
    try {
      setCategories(await fetchCategories())
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load categories.')
    } finally {
      setListLoading(false)
    }
  }

  useEffect(() => {
    async function load() {
      try {
        await loadCategories()
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Unable to load categories.')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  async function handleSubmit(payload: CategoryWriteRequest) {
    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      if (editingCategory) {
        await updateCategory(editingCategory.id, payload)
        setSuccess('Category updated successfully.')
        setEditingCategory(null)
      } else {
        await createCategory(payload)
        setSuccess('Category created successfully.')
      }
      await loadCategories()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to save category.')
      throw submitError
    } finally {
      setSubmitting(false)
    }
  }

  async function handleEdit(categoryId: number) {
    setError('')
    setSuccess('')
    setEditingCategoryId(categoryId)
    try {
      setEditingCategory(await fetchCategory(categoryId))
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load category.')
    } finally {
      setEditingCategoryId(null)
    }
  }

  async function handleToggleStatus(category: Category) {
    setError('')
    setSuccess('')
    setStatusUpdatingId(category.id)
    try {
      await setCategoryStatus(category.id, !category.is_active)
      setSuccess(`Category ${category.is_active ? 'deactivated' : 'activated'} successfully.`)
      await loadCategories()
    } catch (statusError) {
      setError(statusError instanceof Error ? statusError.message : 'Unable to update category status.')
    } finally {
      setStatusUpdatingId(null)
    }
  }

  return (
    <div className="product-page">
      <div className="page-intro">
        <div>
          <p className="eyebrow">Catalog setup</p>
          <h1>Category Master</h1>
          <p className="page-description">Organize products into clear catalog categories.</p>
        </div>
        <div className="page-mark">CM<span>04</span></div>
      </div>
      {error && <div className="notice notice--error" role="alert"><strong>Something needs attention</strong><span>{error}</span></div>}
      {success && <div className="notice notice--success" role="status"><strong>Saved</strong><span>{success}</span></div>}
      {loading ? <div className="loading-panel">Preparing your category workspace...</div> : <>
        <CategoryForm
          key={editingCategory?.id ?? 'create'}
          submitting={submitting}
          editingCategory={editingCategory}
          onSubmit={handleSubmit}
          onCancelEdit={() => setEditingCategory(null)}
        />
        <CategoryList
          categories={categories}
          loading={listLoading}
          onEdit={handleEdit}
          onToggleStatus={handleToggleStatus}
          editingCategoryId={editingCategoryId}
          statusUpdatingId={statusUpdatingId}
        />
      </>}
    </div>
  )
}