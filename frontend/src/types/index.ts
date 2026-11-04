export type Label = 'HARD' | 'REPORTED' | 'ESTIMATE' | 'N/A' | string

export interface Fund { name: string; size_usd_bn: number | null; vintage: number | null; label?: Label }
export interface KeyPerson { name: string; title: string; focus: string }

export interface ManagerRow {
  id: string
  name: string
  type: string
  hq: string
  founded: number | null
  aum_usd_bn: number | null
  aum_label: Label
  stages: string[]
  focus_areas: string[]
  key_people_names: string[]
  latest_fund: Fund | null
  n_companies: number
  is_stub: boolean
  recent_activity: string
  research_status: ResearchStatus
  added_via: string
}

export interface Holding {
  company_id: string
  name: string
  sector: string
  status: string
  latest_valuation_usd_bn: number | null
  revenue_usd_bn: number | null
  legacy: boolean
  valuation_stale: boolean
  first_invest_year: number | null
  entry_round: string
  lead: boolean
  via: string
  entry_post_usd_bn: number | null
  markup_x: number | null
}

export interface ManagerDetail {
  id: string
  name: string
  website: string
  portfolio_url: string
  hq: string
  other_offices: string[]
  founded: number | null
  type: string
  aum_usd_bn: number | null
  aum_label: Label
  aum_date: string
  overview: string
  check_size: string
  stages: string[]
  focus_areas: string[]
  team_size: string
  team_label: Label
  performance: string
  performance_label: Label
  best_performers: string[]
  notable_exits: string[]
  recent_activity: string
  watch_items: string
  sources: string[]
  last_verified: string
  is_stub: boolean
  research_status: ResearchStatus
  added_via: string
  recent_funds: Fund[]
  key_people: KeyPerson[]
  holdings: Holding[]
}

export interface CompanyRow {
  id: string
  name: string
  description: string
  sector: string
  focus_tags: string[]
  status: string
  hq: string
  ceo: string
  latest_valuation_usd_bn: number | null
  valuation_date: string
  valuation_label: Label
  valuation_stale: boolean
  legacy: boolean
  first_mark_date: string
  step_up_x: number | null
  revenue_usd_bn: number | null
  revenue_metric: string
  revenue_date: string
  ev_rev_x: number | null
  growth: string
  profitability: string
  total_raised_usd_bn: number | null
  founded: number | null
  tracked_gp_ids: string[]
  other_investors: string[]
  research_status: ResearchStatus
  added_via: string
}

export interface Round { date: string; round: string; post_money_usd_bn: number | null; lead: string }

export interface Position {
  firm_id: string
  firm_name: string
  first_invest_year: number | null
  entry_round: string
  fund: string
  lead: boolean
  via: string
  entry_post_usd_bn: number | null
  markup_x: number | null
}

export interface CompanyDetail extends Omit<CompanyRow, 'tracked_gp_ids'> {
  website: string
  valuation_basis: string
  first_mark_usd_bn: number | null
  revenue_label: Label
  employees: number | null
  notes: string
  sources: string[]
  last_verified: string
  valuation_history: Round[]
  gp_positions: Position[]
}

export interface RecentRound { company_id: string; date: string; round: string; post_money_usd_bn: number | null; lead: string }
export interface ChangeRow { date: string; company_id: string | null; company_name: string; type: string; from: number | null; to: number | null; detail: string }
export interface RefreshRow { date: string; managers: number; companies: number; changes: number; source: string }

export interface Meta {
  asof: string | null
  managers: number
  companies: number
  legacy_companies: number
  combined_value_usd_bn: number
  combined_aum_usd_bn: number
  consensus_names: number
  refresh_log: RefreshRow[]
}

export interface Watchlist { managers: string[]; companies: string[] }

export type ResearchStatus = '' | 'queued' | 'running' | 'failed'

export interface ResearchJob {
  id: string
  kind: 'manager' | 'company'
  name: string
  slug: string
  status: 'queued' | 'running' | 'done' | 'failed'
  error: string
  summary: string
  include_portfolio: boolean
  children_total: number
  children_done: number
  children_failed: number
  searches: number
  cost_usd: number
  model: string
  portfolio_model: string
  portfolio_limit: number
  created_at: string
  finished_at: string | null
}

export interface ResearchModel { id: string; label: string; est_manager: number; est_company: number }

export interface ResearchState {
  enabled: boolean
  can_research: boolean
  active: number
  jobs: ResearchJob[]
  models: ResearchModel[]
  defaults: { manager: string; portfolio: string; company: string }
  max_portfolio: number
}

export interface AddOptions { model?: string; portfolio_model?: string; portfolio_limit?: number; include_portfolio?: boolean }

// ── Track record ────────────────────────────────────────────────────────────
export type Severity = 'high' | 'medium' | 'low'
export interface Point { text: string; severity: Severity }
export interface LpComment { id: number; author_name: string; text: string; created_at: string }
export interface CashFlowRow { date: string; amount_usd_m: number | null; note: string }

export interface InvMetrics {
  invested_usd_m: number | null; realised_usd_m: number | null; current_usd_m: number | null
  total_value_usd_m: number | null; gain_usd_m: number | null
  gross_moic: number | null; gross_irr: number | null; dpi: number | null; rvpi: number | null
  net_moic: number | null; net_irr: number | null; net_dpi: number | null; net_basis: 'reported' | 'estimate' | 'no fees'
  fees_usd_m: number | null; carry_usd_m: number | null; holding_years: number | null; irr_nm: boolean
  unfunded_usd_m: number | null; ownership_pct: number | null; implied_markup_x: number | null; suggested_value_usd_m: number | null
}

export type Structure = 'direct' | 'spv' | 'coinvest' | 'l1' | 'l2' | 'secondary'
export type InvStatus = 'active' | 'partial' | 'realised' | 'written_off'

export interface LpInvestment {
  id: number
  name: string
  company_id: string | null
  manager_id: string | null
  manager_name: string
  is_fund: boolean
  vintage: number | null
  description: string
  sector: string
  hq: string
  structure: Structure
  structure_label: string
  vehicle: string
  round: string
  lead_investors: string[]
  co_investors: string[]
  invest_date: string
  commitment_usd_m: number | null
  invested_usd_m: number | null
  entry_valuation_usd_bn: number | null
  ownership_pct: number | null
  current_value_usd_m: number | null
  value_date: string | null
  value_basis: string
  realised_usd_m: number | null
  mgmt_fee_pct: number | null
  carry_pct: number | null
  net_moic_reported: number | null
  net_irr_reported: number | null
  dpi_reported: number | null
  capacity_usd_m: number | null
  status: InvStatus
  status_label: string
  highlight: string
  thesis: string
  pros: Point[]
  cons: Point[]
  risks: Point[]
  include_in_sheet: boolean
  order: number
  cashflows: CashFlowRow[]
  comments: LpComment[]
  metrics: InvMetrics
}

export interface TrSummary {
  count: number; active?: number; invested_usd_m?: number; realised_usd_m?: number; current_usd_m?: number
  total_value_usd_m?: number; gross_moic?: number | null; net_moic?: number | null; dpi?: number | null
  gross_irr?: number | null; net_irr?: number | null; capacity_usd_m?: number; unfunded_usd_m?: number
  best?: { name: string; gross_moic: number | null }
}

export interface SheetSettings {
  title: string; subtitle: string; prepared_by: string; contact: string; disclaimer: string; show_capacity: boolean
  fund_title: string; fund_subtitle: string
}

export interface FundBucket {
  count: number; commitment_usd_m: number; called_usd_m: number; distributed_usd_m: number; nav_usd_m: number
  total_value_usd_m: number; unfunded_usd_m: number; pct_called: number | null; tvpi: number | null; dpi: number | null
  rvpi: number | null; net_irr: number | null; vintage?: number; strategy?: string
}

export interface FundProgramme extends Partial<FundBucket> { count: number; gps?: number; by_vintage: FundBucket[]; by_strategy: FundBucket[] }

export interface TrackRecordData {
  investments: LpInvestment[]
  summary: TrSummary
  summary_direct: TrSummary
  summary_funds: TrSummary
  sheet_summary: TrSummary
  fund_programme: FundProgramme
  settings: SheetSettings
  can_edit: boolean
}

export interface Assessment {
  view: string; pros: Point[]; cons: Point[]; risks: Point[]; updated_by: string; updated_at: string | null
  comments: LpComment[]; commitments: LpInvestment[]
}
