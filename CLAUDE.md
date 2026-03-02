# SalesCount - WhatsApp AI Sales Platform
## Complete Project Context & Architecture

**Last Updated:** March 2, 2026
**Current Status:** Production-Ready with Sample Data
**Test Suite:** 194 tests passing (100%)

---

## 🎯 Project Overview

**SalesCount** is a comprehensive WhatsApp AI-powered sales platform that helps merchants automate customer engagement, track conversions, manage campaigns, and optimize billing. The platform is built with Django 5.0 backend, Next.js 14 frontend, PostgreSQL database, and Redis caching.

### Core Value Proposition
- **WhatsApp Integration**: Send targeted product messages via WhatsApp
- **AI Chatbot**: Intelligent conversation stages (greeting → qualifying → pitching → closing)
- **Click Tracking**: Monitor which products customers click with fraud detection
- **Conversion Attribution**: Track purchases with HMAC-signed postbacks
- **Merchant Dashboard**: Real-time analytics, campaign management, billing
- **Admin Console**: Multi-merchant oversight, creative approval, dispute resolution

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js 14)                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  Merchant Portal │  │   Admin Console  │  │ Public Docs  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (REST API)
┌─────────────────────────────────────────────────────────────────┐
│                    NGINX Reverse Proxy (Rate Limiting)          │
│  ├─ Auth: 5 req/min       ├─ Webhooks: 20 req/min              │
│  ├─ API: 30 req/sec       └─ Static Files: Cached 30d          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (Django 5.0 + DRF)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Auth     │ │Merchants │ │Campaigns │ │Tracking  │           │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤           │
│  │Billing   │ │Analytics │ │Conversat │ │ SKU/Prom │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Gunicorn (4 gthread workers) + WhiteNoise + Health Check │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
            ↓ ORM           ↓ Cache          ↓ Broker
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ PostgreSQL   │ │ Redis Cache  │ │ Redis Broker │
    │ (15-alpine)  │ │ (7-alpine)   │ │ (Celery)     │
    └──────────────┘ └──────────────┘ └──────────────┘
            ↓                              ↓
        ┌──────────────┐          ┌──────────────────┐
        │ Migrations   │          │ Celery Tasks     │
        │ Fixtures     │          │ Beat Scheduler   │
        │ Seeds        │          │ Flower Monitor   │
        └──────────────┘          └──────────────────┘
```

---

## 🏗️ Database Schema (Key Models)

### Users & Merchants
- **User** (AbstractUser): role (admin/merchant/agent), phone, is_verified, created_at
- **MerchantProfile**: company_name, contact_email, billing_address, status (pending/approved/rejected/suspended), tier (bronze/silver/gold/platinum), commission_rate (4-10%), daily_budget_cap, hmac_secret, razorpay_customer_id, whatsapp_number

### Products & Promotions
- **SKU**: sku_code, name, description, category, original_price, discounted_price, landing_url, stock_quantity, is_active
- **PromoRule**: name, promo_type (percentage/fixed/free_shipping), value, coupon_prefix, max_uses, valid_from/until, applicable_skus (M2M)

### Campaigns
- **Campaign**: name, description, status (draft/active/paused/ended), target_skus (M2M), start_date, end_date, daily_message_limit, messages_sent_today
- **CampaignCreative**: greeting_template, pitch_template, close_template, is_approved, approved_by (admin-only approval workflow)
- **ABTestVariant**: name, variant_type, config_json, traffic_weight, impressions, conversions, is_active

### Conversations & Messaging
- **Conversation**: phone_number, merchant (FK), campaign (FK), stage (greeting/qualifying/narrowing/pitching/closing/objection_handling/ended), ab_variant, context_json, recommended_skus (M2M), coupon_code, is_opted_out, handed_off_to (agent), started_at, last_message_at, ended_at
- **Message**: conversation (FK), direction (inbound/outbound/agent), body, stage_at_send, media_url, openai_tokens_used, created_at
- **FollowUpSchedule**: conversation (FK), scheduled_at, message_template, is_sent

### Click Tracking & Fraud Detection
- **RedirectToken**: token (UUID), conversation (FK), sku, merchant, campaign, destination_url, is_active, created_at, expires_at (72h)
- **ClickEvent**: redirect_token (FK), ip_address, user_agent, referer, country_code, is_fraudulent, fraud_score, fraud_reasons (JSON), clicked_at
- **FraudFlag**: click_event (FK), flag_type (rate_limit/token_reuse/low_dwell/ip_cluster/bot_ua), details, reviewed, reviewed_by, reviewed_at

### Billing & Conversions
- **ConversionEvent**: merchant (FK), click_event (FK), order_id, order_amount, commission_amount, converted_at, is_valid, is_disputed
- **DisputeRecord**: merchant (FK), conversion_event (FK), reason, status (open/upheld/rejected), resolved_by (admin), resolved_at, credit_amount
- **Invoice**: merchant (FK), invoice_number, period_start/end, total_conversions, subtotal, total, due_date, status (draft/sent/paid/overdue)
- **InvoiceLine**: invoice (FK), conversion_event (FK), billing_type (cpa), quantity, unit_price, line_total

### Analytics
- **DailyMerchantStats**: merchant, date, conversations_started, messages_sent, clicks_total, clicks_valid, conversions, revenue_gross, spend, ctr, conversion_rate
- **DailyCampaignStats**: campaign, date, impressions, clicks, conversions, spend, ctr, conversion_rate
- **HourlyClickStats**: merchant, hour, clicks, valid_clicks

---

## 🚀 API Endpoints by Module

### Authentication (`/api/v1/auth/`)
- `POST /register/` - Create new merchant account
- `POST /login/` - Get access + refresh tokens (JWT)
- `POST /refresh/` - Refresh expired access token
- `GET /me/` - Current user profile

### Merchants (`/api/v1/merchants/`)
- `GET/PUT /profile/` - My profile (merchant only)
- `POST /onboard/` - KYC onboarding
- `GET/PUT /billing-settings/` - Billing config
- `GET/POST /skus/` - Product management (merchant can only see own)
- `GET/POST /promo-rules/` - Promotion rules
- `GET /admin/list/` - All merchants (admin only)
- `POST /admin/{id}/{action}/` - Approve/reject/suspend merchant (admin only)

### Campaigns (`/api/v1/campaigns/`)
- `GET/POST /` - List/create campaigns (merchant sees own, admin sees all)
- `GET/PUT/DELETE /{id}/` - Campaign CRUD
- `POST /{id}/activate/` - Change status to active
- `POST /{id}/pause/` - Change status to paused
- `GET/POST /{id}/creatives/` - Campaign creatives
- `GET/POST /{id}/ab-variants/` - A/B test variants

### Conversations (`/api/v1/conversations/`)
- `GET/POST /` - List/create conversations
- `GET/PUT/PATCH /{id}/` - Conversation detail + stage updates
- `GET /{id}/messages/` - Conversation messages
- `POST /{id}/messages/` - Send message from agent
- `POST /{id}/handoff/` - Handoff to human agent
- `POST /{id}/opt-out/` - Opt-out customer

### WhatsApp Webhook (`/api/v1/whatsapp/`)
- `POST /webhook/` - Receive incoming messages from Twilio

### Click Tracking (`/api/v1/tracking/`)
- `GET /t/{token}/` - Follow redirect (302 → destination_url, creates ClickEvent)
- `GET/POST /clicks/` - List clicks (admin only, supports fraud_only filter)
- `GET /clicks/{id}/` - Click detail + fraud flags
- `GET /fraud-flags/` - Pending fraud reviews
- `PUT /fraud-flags/{id}/review/` - Mark as reviewed (admin)

### Billing (`/api/v1/billing/`)
- `POST /postback/` - Receive conversion postback (HMAC-signed)
- `POST /coupon-redeem/` - Redeem coupon code (HMAC-signed)
- `GET /conversions/` - List conversions (merchant/admin)
- `GET /invoices/` - List invoices (merchant/admin)
- `GET /invoices/{id}/` - Invoice detail with line items
- `GET /disputes/` - List disputes (merchant/admin)
- `POST /disputes/{id}/resolve/` - Admin resolves dispute (upheld/rejected)
- `GET /revenue-stats/` - Revenue overview (admin only)

### Analytics (`/api/v1/analytics/`)
- `GET /admin/dashboard/` - KPI cards (admin only, supports period filter)
- `GET /admin/trends/` - Daily time-series (admin only)
- `GET /admin/funnel/` - Conversation→Click→Conversion funnel (admin only)
- `GET /admin/top-merchants/` - Top 10 merchants by revenue (admin only)
- `GET /merchant/dashboard/` - KPI cards (merchant only)
- `GET /merchant/trends/` - Merchant-scoped daily trends (merchant only)

### Health & Status
- `GET /health/` - Liveness probe (always 200)
- `GET /ready/` - Readiness probe (checks DB + cache, returns 503 if degraded)

---

## 🔐 Security & Production Hardening

### Authentication & Authorization
- **JWT Tokens**: 15-min access, 7-day refresh, rotate on refresh, blacklist after rotation
- **Role-Based Access**: IsAdmin, IsMerchant, IsAgent, IsAdminOrMerchant permissions
- **HMAC Signing**: Postback/coupon requests validated with merchant-specific hmac_secret
- **Timestamp Freshness**: Requests must be within 5 minutes (prevents replay attacks)

### Rate Limiting (Nginx)
- **Auth endpoints**: 5 req/min per IP
- **Webhooks (WhatsApp/Razorpay)**: 20 req/min per IP
- **General API**: 30 req/sec per IP
- **DRF Throttling**: 100/hour anon, 1000/hour user

### Security Headers
- **X-Frame-Options**: DENY (prevent clickjacking)
- **X-Content-Type-Options**: nosniff (MIME sniffing)
- **Referrer-Policy**: strict-origin-when-cross-origin
- **Permissions-Policy**: camera=(), microphone=(), geolocation=()
- **HSTS**: 1 year with subdomains + preload (production only)

### Database
- **CONN_MAX_AGE**: 600 seconds (persistent connections)
- **CONN_HEALTH_CHECKS**: True (detect stale connections)
- **select_related / prefetch_related**: Used throughout to minimize N+1 queries

### Celery Task Security
- **Soft timeout**: 5 minutes, hard kill at 10 minutes
- **Acks late**: Tasks re-queued if worker dies mid-execution
- **Worker recycling**: Max 1000 tasks per worker before restart
- **Prefetch**: 1 task per worker (no memory buildup)

### WhiteNoise (Production)
- Serves static files efficiently without nginx
- Gzip compression + browser caching headers
- Manifest file for cache busting

### Logging & Monitoring
- **Request ID**: Every request gets X-Request-ID UUID for tracing
- **Request Logging**: All requests logged with method, path, status, duration, user_id
- **Structured Logging**: JSON-capable format for log aggregators
- **Sentry Integration**: Production error tracking with Redis integration

---

## 📅 Celery Beat Schedule (Automated Tasks)

| Task | Frequency | Purpose |
|------|-----------|---------|
| `aggregate_hourly_stats` | Every hour @ :05 | Compute HourlyClickStats for dashboards |
| `aggregate_daily_stats` | 1:00 AM UTC | DailyMerchantStats, DailyCampaignStats aggregation |
| `check_daily_budget_caps` | Every 15 min | Pause campaigns if merchant exceeds daily budget |
| `generate_weekly_invoices` | Monday 2 AM UTC | Create invoices + send to Razorpay |
| `update_merchant_tiers` | 1st of month 3 AM UTC | Recalculate tiers (bronze→gold) based on revenue |

---

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 5.0, Django REST Framework 3.15
- **Database**: PostgreSQL 15 (Alpine)
- **Cache**: Redis 7 (Alpine)
- **Task Queue**: Celery 5.3 + Django Celery Beat
- **API Server**: Gunicorn 21.2 (4 gthread workers)
- **Security**: django-cors-headers, djangorestframework-simplejwt, django-csp
- **Monitoring**: Sentry SDK, django-extensions
- **Payment**: Razorpay API (CPA billing)
- **External APIs**: Twilio (WhatsApp), OpenAI (chatbot), Pinecone (embeddings)

### Frontend
- **Framework**: Next.js 14 (React 18)
- **State**: React hooks + Axios
- **Charts**: Recharts 2.12 (area, bar, line charts)
- **Styling**: Tailwind CSS 3.4
- **Icons**: Lucide React
- **Form Validation**: React built-in form APIs

### DevOps
- **Containerization**: Docker + docker-compose (dev & prod)
- **Web Server**: Nginx 1.25-alpine (reverse proxy + rate limiting)
- **Database Migrations**: Django migrations system
- **Monitoring**: Flower (Celery monitoring), health endpoints

---

## 📁 Project Structure

```
SalesCount/
├── backend/
│   ├── salescount/
│   │   ├── settings/
│   │   │   ├── base.py          (Shared config: DB, Cache, Celery, Logging)
│   │   │   ├── dev.py           (SQLite, LocMemCache, DEBUG=True)
│   │   │   └── prod.py          (WhiteNoise, SECURE_SSL_REDIRECT, Sentry)
│   │   ├── urls.py              (/health, /ready, /api/v1/*)
│   │   ├── wsgi.py              (Gunicorn entry point)
│   │   └── celery.py            (Celery app config)
│   ├── apps/
│   │   ├── accounts/            (User model, auth endpoints, seed command)
│   │   ├── merchants/           (Profile, SKU, PromoRule models)
│   │   ├── campaigns/           (Campaign, Creative, ABTestVariant models + views)
│   │   ├── conversations/       (Conversation, Message, FollowUpSchedule models)
│   │   ├── tracking/            (RedirectToken, ClickEvent, FraudFlag models)
│   │   ├── billing/             (ConversionEvent, Invoice, DisputeRecord models + Razorpay)
│   │   └── analytics/           (Daily/Hourly stats models + dashboard views)
│   ├── common/
│   │   ├── health.py            (Health check endpoints)
│   │   ├── middleware.py        (Request ID + Request logging)
│   │   ├── permissions.py       (Role-based permissions)
│   │   ├── throttling.py        (DRF rate limiting classes)
│   │   ├── pagination.py        (StandardPagination: 20 per page, max 100)
│   │   ├── exceptions.py        (Custom exception classes with status codes)
│   │   ├── hmac_utils.py        (HMAC signing for postbacks)
│   │   └── tests/test_production.py (54 production hardening tests)
│   ├── requirements/
│   │   ├── base.txt             (All deps)
│   │   ├── dev.txt              (+ pytest, debug-toolbar, ruff)
│   │   └── prod.txt             (+ whitenoise)
│   ├── gunicorn.conf.py         (Production server config)
│   ├── Dockerfile               (Multi-stage: dev/prod targets)
│   ├── manage.py
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (merchant)/      (Merchant portal routes)
│   │   │   │   ├── dashboard/   (KPI cards + charts)
│   │   │   │   ├── campaigns/   (List + new form + detail)
│   │   │   │   ├── settings/    (Billing, integrations)
│   │   │   │   └── layout.tsx   (Sidebar + header)
│   │   │   ├── admin/           (Admin console routes)
│   │   │   │   ├── dashboard/   (Trends + funnel + top merchants)
│   │   │   │   ├── campaigns/   (All campaigns + creative approval)
│   │   │   │   ├── billing/     (Revenue, invoices, disputes)
│   │   │   │   └── layout.tsx
│   │   │   ├── login/           (JWT login)
│   │   │   ├── register/        (Merchant signup)
│   │   │   └── layout.tsx       (Root layout)
│   │   ├── components/
│   │   │   ├── ui/              (Button, Card, Input, Badge components)
│   │   │   └── shared/          (StatusBadge, Chart components)
│   │   ├── lib/
│   │   │   ├── api.ts           (Axios instance + JWT interceptors)
│   │   │   └── utils.ts         (formatCurrency, formatDate, formatPercent, cn)
│   │   ├── types/
│   │   │   ├── campaign.ts      (Campaign, CampaignCreative, ABTestVariant)
│   │   │   ├── billing.ts       (Invoice, ConversionEvent, DisputeRecord)
│   │   │   └── analytics.ts     (TrendDataPoint, FunnelStep, TopMerchant)
│   │   └── styles/global.css    (Tailwind imports)
│   ├── package.json             (Next.js, React, Recharts, Tailwind, Axios)
│   ├── tsconfig.json
│   ├── next.config.js
│   └── Dockerfile               (Node build + serve)
├── backend/nginx/
│   ├── Dockerfile               (Nginx 1.25-alpine)
│   └── nginx.conf               (Proxy + rate limiting + security headers)
├── docker-compose.yml           (Dev: SQLite, LocMemCache, hot reload)
├── docker-compose.prod.yml      (Prod: PostgreSQL, Redis, gunicorn, non-root)
├── .env.example
└── README.md
```

---

## 🧪 Testing & Quality Assurance

### Test Coverage (194 Tests, 100% Pass Rate)

| Module | Tests | Coverage |
|--------|-------|----------|
| Conversations | 33 | Bot engine, stages, A/B testing, coupons, opt-out |
| Tracking | 35 | Redirect tokens, click events, fraud detection |
| Billing | 50 | Postbacks, invoices, disputes, Razorpay webhooks, HMAC |
| Analytics | 22 | Dashboard KPIs, trends, funnels, daily aggregation |
| Production (Phase 7) | 54 | Health checks, middleware, throttling, permissions, Celery schedule |

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific module
python manage.py test apps.billing

# With coverage
pytest --cov=apps
```

---

## 🎛️ Sample Data & Development

### Seed Command
```bash
python manage.py seed_data           # Seed everything
python manage.py seed_data --flush   # Clear then seed
```

**Generated Sample Data:**
- 4 merchants (TechMart, FashionHub, HomeStyle, HealthPlus) with logins
- 18 SKUs (5 per merchant)
- 5 promo rules (percentage, fixed, free shipping)
- 8 campaigns (mix of draft, active, paused, ended)
- 80 conversations (with 2-8 messages each)
- 122 redirect tokens
- 153 click events (15 fraudulent)
- 35 conversions
- 4 invoices with line items

**Test Credentials:**
- Admin: `admin` / `admin1234`
- Merchants: `merchant_{techmart|fashionhub|homestyle|healthplus}` / `merchant1234`

---

## 🚀 Deployment & Running

### Development
```bash
# Start all services (docker-compose)
docker-compose up

# Or manually
python manage.py runserver 0.0.0.0:8000  # Backend
npm run dev                                # Frontend
celery -A salescount worker -l info       # Celery
celery -A salescount beat -l info         # Beat scheduler
```

### Production
```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Run
docker-compose -f docker-compose.prod.yml up -d

# Migrate & seed
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
docker-compose -f docker-compose.prod.yml exec web python manage.py seed_data
```

---

## 📋 Key Features by Phase

| Phase | Features | Status |
|-------|----------|--------|
| 1 | User auth, merchant onboarding, SKU/promo management | ✅ Complete |
| 2 | Merchant portal, admin dashboard, role-based access | ✅ Complete |
| 3 | WhatsApp chatbot, conversation stages, A/B testing | ✅ Complete |
| 4 | Click tracking, fraud detection, redirect tokens | ✅ Complete |
| 5 | Billing system, invoicing, Razorpay integration, disputes | ✅ Complete |
| 6 | Analytics dashboards, charts, daily aggregation | ✅ Complete |
| 7 | Production hardening, health checks, Celery schedule | ✅ Complete |

---

## 🔄 Recent Improvements (Phase 7 + Campaign Creation)

### Production Hardening
- ✅ Health check endpoints (`/health/`, `/ready/`)
- ✅ Request ID middleware (X-Request-ID for tracing)
- ✅ Structured logging (request duration, user_id, status)
- ✅ Celery task limits (5m soft, 10m hard kill)
- ✅ Worker recycling (max 1000 tasks)
- ✅ WhiteNoise for static files
- ✅ Multi-stage Dockerfile (dev/prod targets)
- ✅ docker-compose.prod.yml with resource limits

### Campaign Creation Feature
- ✅ Frontend form page (`/campaigns/new/`)
- ✅ SKU + promo rule selectors
- ✅ Date/time pickers
- ✅ Form validation + error display
- ✅ Backend integration with merchant auto-assignment
- ✅ Create Campaign button wired

### Sample Data
- ✅ Management command `seed_data`
- ✅ 4 merchants with different industries
- ✅ 18 products across categories
- ✅ 8 campaigns in various states
- ✅ 80 conversations with message history
- ✅ 153 clicks + 35 conversions
- ✅ Fraud data (8% fraud rate)

---

## 🎯 Next Steps (If Continuing)

1. **Create Additional Frontend Pages**
   - Creative creation/approval workflow
   - A/B variant configuration
   - Dispute resolution UI
   - Conversation handoff interface

2. **Mobile App**
   - React Native version for agents
   - Real-time message notifications
   - Offline conversation support

3. **Advanced Analytics**
   - Predictive churn modeling
   - Cohort analysis
   - Attribution modeling

4. **Performance Optimization**
   - Database query optimization (N+1 analysis)
   - Frontend code splitting by route
   - GraphQL API alternative

5. **Compliance**
   - GDPR data export/deletion
   - PII redaction logging
   - Audit trails for sensitive actions

---

## 📞 Support & Debugging

### Useful Commands
```bash
# View logs
docker-compose logs -f web                    # Backend
docker-compose logs -f worker                 # Celery worker
docker-compose logs -f beat                   # Beat scheduler

# Access shell
docker-compose exec web python manage.py shell

# Database shell
docker-compose exec db psql -U salescount -d salescount

# Migrate
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Flush & seed
docker-compose exec web python manage.py seed_data --flush
```

### Common Issues
- **"CORS error in frontend"**: Check `CORS_ALLOWED_ORIGINS` in settings
- **"Celery tasks not running"**: Verify Redis is accessible, check Beat scheduler
- **"Static files 404"**: Run `collectstatic`, check WhiteNoise in middleware
- **"Database migrations stuck"**: Delete `.migrations/__pycache__`, re-run migrate
- **"Postback signature fails"**: Verify merchant hmac_secret matches client implementation

---

## 📝 Notes for Future Developers

1. **Always use select_related/prefetch_related** - We avoid N+1 queries aggressively
2. **Test rate limiting** - All webhook endpoints have custom throttle classes
3. **HMAC is canonical** - Field order matters in signatures (see `common/hmac_utils.py`)
4. **Conversation stages are sequential** - The bot engine enforces stage transitions
5. **Fraud score is cumulative** - Multiple flags can increase fraud_score beyond individual thresholds
6. **Invoices are one-week** - `generate_invoices` runs weekly, not daily
7. **Merchant tiers recalculate monthly** - Based on prior month's revenue
8. **Campaign status updates pause/resume** - No explicit "campaign paused" webhook to merchants

---

**Built with ❤️ using Django, Next.js, and PostgreSQL**
