export interface AdminDashboard {
  total_conversations: number;
  total_clicks: number;
  flagged_clicks: number;
  total_conversions: number;
  total_revenue: number;
  conversion_rate: number;
  active_merchants: number;
}

export interface MerchantDashboard {
  conversations_today: number;
  clicks_today: number;
  conversions_today: number;
  ctr: number;
  spend_today: number;
  daily_budget_cap: number;
  budget_remaining: number;
}

export interface TrendDataPoint {
  date: string;
  clicks: number;
  conversions: number;
  conversations: number;
  revenue?: number;
  spend?: number;
  fraudulent?: number;
}

export interface FunnelStep {
  stage: string;
  count: number;
}

export interface TopMerchant {
  merchant: string;
  revenue: number;
  conversions: number;
}
