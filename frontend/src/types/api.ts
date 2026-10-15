export type RiskLevel = 'low' | 'medium' | 'high'
export type Customer = { id: string; external_customer_id: string; name: string | null; features: Record<string, unknown>; created_at: string; last_prediction?: Prediction | null }
export type Prediction = { prediction: boolean; probability: number; risk_level: RiskLevel; important_factors: Factor[]; model_version: string; prediction_id: string; customer_id?: string | null; created_at?: string }
export type Factor = { feature_name: string; display_name: string; impact: number; direction: string; value?: string; rank: number }
export type DashboardSummary = { customer_count: number; dataset_count: number; prediction_count: number; high_risk_count: number; medium_risk_count: number; low_risk_count: number; predicted_churn_rate: number; average_probability: number; active_model: { id: string; version: string; metrics: Record<string, number> }; recent_predictions: Prediction[] }
export type Model = { id: string; version: string; algorithm: string; status: string; metrics: Record<string, number> }
export type Dataset = { id: string; name: string; status: string; row_count: number; columns: string[]; validation_summary: { errors?: string[]; warnings?: string[] }; target_column?: string | null; created_at: string }
export type Analytics = { total_predictions: number; predicted_churn: number; risk_distribution: Record<string, number>; series: unknown[] }
