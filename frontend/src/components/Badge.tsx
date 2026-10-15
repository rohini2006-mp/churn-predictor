import type { RiskLevel } from '../types/api'
export function RiskBadge({ level }: { level: RiskLevel }) { return <span className={`badge badge-${level}`}><span className="badge-dot" />{level.toUpperCase()}</span> }
export function StatusPill({ children }: { children: React.ReactNode }) { return <span className="status-pill">{children}</span> }
