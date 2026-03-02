export interface Campaign {
  id: number;
  name: string;
  description: string;
  status: 'draft' | 'active' | 'paused' | 'ended';
  target_skus: number[];
  promo_rule: number | null;
  start_date: string;
  end_date: string | null;
  daily_message_limit: number;
  messages_sent_today: number;
  created_at: string;
  updated_at: string;
}

export interface CampaignCreative {
  id: number;
  campaign: number;
  name: string;
  greeting_template: string;
  pitch_template: string;
  close_template: string;
  is_approved: boolean;
  approved_by: number | null;
  created_at: string;
}

export interface ABTestVariant {
  id: number;
  campaign: number;
  name: string;
  variant_type: string;
  config_json: Record<string, unknown>;
  traffic_weight: number;
  impressions: number;
  conversions: number;
  conversion_rate: number;
  is_active: boolean;
  created_at: string;
}
