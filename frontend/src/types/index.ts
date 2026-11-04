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
