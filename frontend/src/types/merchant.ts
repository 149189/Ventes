export interface MerchantProfile {
  id: number;
  company_name: string;
  company_website: string;
  contact_email: string;
  contact_phone: string;
  billing_address: string;
  tax_id: string;
  status: 'pending' | 'approved' | 'rejected' | 'suspended';
  tier: 'bronze' | 'silver' | 'gold' | 'platinum';
  commission_rate: number;
  auto_optimize_commission: boolean;
  daily_budget_cap: number;
  billing_model: 'cpa' | 'cpc';
  dispute_window_days: number;
  whatsapp_number: string;
  approved_at: string | null;
  created_at: string;
}

export interface SKU {
  id: number;
  sku_code: string;
  name: string;
  description: string;
  category: string;
  original_price: number;
  discounted_price: number | null;
  landing_url: string;
  image_url: string;
  stock_quantity: number;
  is_active: boolean;
  created_at: string;
}

export interface PromoRule {
  id: number;
  name: string;
  promo_type: 'percentage' | 'fixed' | 'free_shipping';
  value: number;
  coupon_prefix: string;
  max_uses: number;
  uses_count: number;
  valid_from: string;
  valid_until: string;
  applicable_skus: number[];
  is_active: boolean;
  created_at: string;
}
