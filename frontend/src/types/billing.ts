export interface Invoice {
  id: number;
  invoice_number: string;
  period_start: string;
  period_end: string;
  total_clicks: number;
  total_conversions: number;
  subtotal: number;
  credits: number;
  total: number;
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'disputed';
  pdf_url: string;
  due_date: string;
  paid_at: string | null;
  created_at: string;
}

export interface ConversionEvent {
  id: number;
  click_event: number | null;
  conversation: number | null;
  merchant: number;
  source: 'postback' | 'coupon';
  order_id: string;
  order_amount: number;
  coupon_code: string;
  commission_amount: number;
  is_valid: boolean;
  is_disputed: boolean;
  converted_at: string;
  created_at: string;
}

export interface DisputeRecord {
  id: number;
  conversion_event: number;
  merchant: number;
  reason: string;
  evidence: Record<string, unknown>;
  status: 'open' | 'under_review' | 'upheld' | 'rejected';
  resolution_notes: string;
  credit_amount: number;
  filed_at: string;
  resolved_at: string | null;
}
