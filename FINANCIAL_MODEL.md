# Ventes — Financial Model

> Complete breakdown of how money flows through the platform: from merchant acquisition to conversion billing, invoicing, and dispute resolution.

---

## Overview

Ventes operates as a **performance-based marketing platform**. Merchants pay **only when a sale happens** — not for impressions or clicks. The platform earns a commission on every successful conversion attributed to a Ventes-powered WhatsApp conversation.

```
Customer → WhatsApp Chat → Clicks Product Link → Buys → Merchant Reports Sale → Ventes Takes Commission
```

---

## 1. Billing Models

### CPA — Cost Per Acquisition (Default)
- Merchant pays a **% commission on the order value** for every verified sale
- Commission rates: **4% to 10%** of the order GMV
- The merchant sets their own rate within this range (auto-optimize available)

### CPC — Cost Per Click *(configured but not primary)*
- Merchant pays per valid click on a tracked product link
- Not the default model; CPA is preferred

---

## 2. Commission Rates & Merchant Tiers

| Tier | Typical Commission Rate | How to Reach |
|------|------------------------|--------------|
| Bronze | 6–10% | New merchants |
| Silver | 5–7% | Growing revenue |
| Gold | 5% | Consistent performer |
| Platinum | 4–5% | Top revenue generator |

- Tiers are **recalculated on the 1st of every month** by the `update_merchant_tiers` Celery task
- Higher tier = lower commission rate = incentive to grow on the platform
- Merchants can also set `auto_optimize_commission = True` to let the system find the optimal rate

---

## 3. Conversion Attribution

A conversion is recorded when either:

### A. Postback (HMAC-signed server-to-server)
1. Customer clicks a tracked link → `RedirectToken` created → `ClickEvent` recorded
2. Customer buys on the merchant's website
3. Merchant's server sends a **signed POST request** to `/api/v1/billing/postback/` with:
   - `merchant_id`, `order_id`, `order_amount`, `click_token`
   - `timestamp` (must be within 5 minutes — replay attack prevention)
   - `hmac_signature` (HMAC-SHA256 of all fields using the merchant's secret)
4. Platform verifies signature → creates `ConversionEvent`
5. Commission = `order_amount × (commission_rate / 100)`

### B. Coupon Redemption
1. Bot generates a unique coupon during the closing stage (e.g. `TECH-XA12B`)
2. Customer uses coupon on checkout
3. Merchant sends a signed `POST /api/v1/billing/coupon-redeem/` request with the coupon code
4. Platform matches coupon to conversation → creates `ConversionEvent`
5. Same commission calculation applies

### HMAC Signature Construction
```
Fields sorted alphabetically → joined as key=value pairs → HMAC-SHA256 with merchant's hmac_secret
```
Each merchant has a unique `hmac_secret` (64-char hex). This prevents:
- Fake conversion reports
- Replay attacks (5-minute timestamp window)
- Merchant impersonation

---

## 4. Daily Budget Cap

- Each merchant sets a `daily_budget_cap` (e.g. Rs. 500/day)
- The Celery task `check_daily_budget_caps` runs every 15 minutes
- If a merchant's spend today >= their cap, their active campaigns are **automatically paused**
- Campaigns resume the next day when the cap resets

---

## 5. Invoicing

### Invoice Generation
- The `generate_weekly_invoices` Celery task runs **every Monday at 2 AM UTC**
- It creates one `Invoice` per merchant covering the past 7 days
- Each `InvoiceLine` maps to a `ConversionEvent`

### Invoice Structure
```
Invoice
  ├── period_start / period_end  (7-day window)
  ├── total_conversions
  ├── subtotal                   (sum of all commission_amounts)
  ├── credits                    (from upheld disputes)
  ├── total = subtotal - credits
  ├── due_date                   (7 days after invoice creation)
  └── InvoiceLines[]
        ├── conversion_event
        ├── billing_type (cpa)
        ├── unit_price   (commission amount)
        └── line_total
```

### Invoice Lifecycle
```
draft → sent → paid
               ↑
           (Razorpay webhook: invoice.paid)

draft → sent → overdue
               ↑
           (Razorpay webhook: invoice.expired)
```

### Razorpay Integration
- Invoices are pushed to **Razorpay** for payment collection
- Merchants pay via Razorpay (UPI, NEFT, cards)
- Webhooks update invoice status: `invoice.paid` → PAID, `invoice.expired` → OVERDUE
- Each merchant has a `razorpay_customer_id` for linking payments

---

## 6. Dispute Resolution

Merchants can dispute a conversion if they believe it was invalid (fraud, return, test order, etc.)

### Dispute Window
- Default: **14 days** from conversion date
- Configurable per merchant (`dispute_window_days`)
- After the window closes, disputes are rejected automatically

### Dispute Flow
```
Merchant files dispute
    ↓
status: open
    ↓
Admin reviews (under_review)
    ↓
       ┌────────────────┐
    upheld            rejected
       │
 credit_amount = commission_amount
 (applied to next invoice as a deduction)
```

### Financial Impact of Upheld Dispute
- `credit_amount` is set to the full `commission_amount` of the disputed conversion
- On the next invoice, `credits` field reflects total upheld dispute credits
- `total = subtotal - credits` — merchant effectively gets a refund for that conversion

---

## 7. Revenue Stats (Platform-Level)

The admin dashboard tracks:

| Metric | Source |
|--------|--------|
| Total Platform Revenue | Sum of all PAID invoice totals |
| Total Invoices | Count of all invoices |
| Paid / Overdue | Status breakdown |
| Open Disputes | Active dispute count |
| Total Credits Issued | Sum of all upheld dispute credit amounts |

---

## 8. Click Tracking & Fraud Detection

Clicks feed into the conversion pipeline — invalid clicks mean invalid conversions.

### Fraud Scoring
Each `ClickEvent` gets a `fraud_score` (0–100). Flags that raise the score:

| Flag | Type | Description |
|------|------|-------------|
| `rate_limit` | Bot | Too many clicks from same IP in short window |
| `token_reuse` | Fraud | Same redirect token clicked multiple times |
| `low_dwell` | Suspicious | Click → postback too fast (bot-speed) |
| `ip_cluster` | Coordinated | Multiple tokens from same IP |
| `bot_ua` | Bot | Known bot user agent string |

- `is_fraudulent = True` if fraud_score is above threshold
- Fraudulent clicks → conversions linked to them can be auto-flagged as `is_valid = False`
- Admin can review and manually resolve fraud flags

---

## 9. Promotional Rules & Coupons

### PromoRule Model
Merchants configure discount rules:
- **Percentage**: e.g. 10% off
- **Fixed Amount**: e.g. Rs. 200 off
- **Free Shipping**: no delivery charge

Rules can be scoped to specific SKUs and have:
- `coupon_prefix` — e.g. `TECH` → generates `TECH-XA12B`
- `max_uses` — cap total redemptions
- `valid_from` / `valid_until` — time window
- `uses_count` — tracked in real-time

### Coupon Generation in Bot
- The bot generates a coupon during the **CLOSING** stage
- A `PromoRule` is selected and a unique code is created
- Code is stored on the `Conversation.coupon_code` field
- When the customer redeems it, the merchant fires the coupon-redeem postback

---

## 10. Follow-Up Revenue Loop

When a conversation enters the CLOSING stage, the bot auto-schedules follow-ups:

| Follow-up | Timing | Purpose |
|-----------|--------|---------|
| First | 24 hours | Re-engage warm lead |
| Second | 3 days | Final nudge before lead goes cold |

Follow-ups are sent via Celery tasks using `send_followup_reminder`. They bring customers back into the conversation → more clicks → more conversions → more revenue.

---

## 11. Money Flow Diagram

```
                    Customer buys
                         │
              ┌──────────┴──────────┐
         via link click        via coupon code
              │                    │
      ClickEvent created    Conversation.coupon_code matched
              │                    │
              └──────────┬─────────┘
                         │
              ConversionEvent created
              commission = order_amount × rate%
                         │
              ┌──────────┴──────────┐
          Valid conversion     Fraudulent / Disputed
              │                    │
        Counted in invoice     is_valid=False or
              │                dispute filed → credit
              │
         Weekly Invoice
         subtotal = Σ commissions
         credits  = Σ upheld disputes
         total    = subtotal - credits
              │
         Sent to Razorpay
              │
    Merchant pays → Invoice → PAID
              │
         Platform Revenue
```

---

## 12. Key Numbers (Seed Data Reference)

| Item | Value |
|------|-------|
| Commission range | 4% – 10% |
| Default commission | 5% |
| Invoice frequency | Weekly (Monday 2 AM UTC) |
| Tier update frequency | Monthly (1st, 3 AM UTC) |
| Daily budget check | Every 15 minutes |
| Dispute window (default) | 14 days |
| Redirect token expiry | 72 hours |
| Timestamp freshness (HMAC) | 5 minutes |
| Sample fraud rate | ~8% of clicks |

---

*Last updated: March 2026*
