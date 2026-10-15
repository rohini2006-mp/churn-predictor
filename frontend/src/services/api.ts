import type { Analytics, Customer, DashboardSummary, Dataset, Model, Prediction } from '../types/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('churnpilot_access_token')
  const response = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(init?.headers || {}) }, ...init })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body?.detail?.message || body?.error?.message || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  authLogin: (email: string, password: string) => request<{ access_token: string; user: { id: string; email: string; display_name: string } }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  authSignup: (email: string, password: string, displayName: string) => request<{ access_token: string; user: { id: string; email: string; display_name: string } }>('/api/auth/signup', { method: 'POST', body: JSON.stringify({ email, password, display_name: displayName }) }),
  authMe: () => request<{ user: { id: string; email: string; display_name: string } }>('/api/auth/me'),
  authLogout: () => request<{ success: boolean }>('/api/auth/logout', { method: 'POST' }),
  dashboard: () => request<DashboardSummary>('/api/dashboard/summary'),
  customers: (search = '') => request<{ items: Customer[]; total: number }>(`/api/customers?limit=50${search ? `&search=${encodeURIComponent(search)}` : ''}`),
  models: () => request<{ items: Model[]; total: number }>('/api/models'),
  predict: (features: Record<string, unknown>, customerId?: string) => request<Prediction>('/api/predict', { method: 'POST', body: JSON.stringify({ features, customer_id: customerId }) }),
  datasets: () => request<{ items: Dataset[]; total: number }>('/api/datasets'),
  datasetPreview: (id: string) => request<{ columns: string[]; rows: Record<string, unknown>[]; validation_summary: Record<string, unknown> }>(`/api/datasets/${id}/preview`),
  deleteDataset: (id: string) => request<void>(`/api/datasets/${id}`, { method: 'DELETE' }),
  uploadDataset: async (file: File, targetColumn = 'churn') => {
    const token = localStorage.getItem('churnpilot_access_token')
    const form = new FormData()
    form.append('file', file)
    form.append('target_column', targetColumn)
    const response = await fetch(`${API_BASE}/api/datasets/upload`, { method: 'POST', body: form, headers: token ? { Authorization: `Bearer ${token}` } : {} })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(body?.detail?.message || 'Dataset upload failed')
    }
    return response.json() as Promise<Dataset>
  },
  train: (datasetId: string) => request<Record<string, unknown>>('/api/models/train', { method: 'POST', body: JSON.stringify({ dataset_id: datasetId, target_column: 'churn' }) }),
  trainingRuns: () => request<{ items: { id: string; dataset_id: string; status: string; metrics?: Record<string, number> }[]; total: number }>('/api/training-runs'),
  churnAnalytics: () => request<Analytics>('/api/analytics/churn'),
  featureAnalytics: () => request<{ items: { display_name: string; occurrences: number; avg_absolute_impact: number }[] }>('/api/analytics/features'),
}
