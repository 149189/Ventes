"""
Management command to seed the database with realistic sample data.

Usage:
    python manage.py seed_data          # Seed everything
    python manage.py seed_data --flush  # Clear existing data first
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.merchants.models import MerchantProfile, SKU, PromoRule
from apps.campaigns.models import Campaign, CampaignCreative, ABTestVariant
from apps.conversations.models import Conversation, Message
from apps.tracking.models import RedirectToken, ClickEvent
from apps.billing.models import ConversionEvent, Invoice, InvoiceLine


class Command(BaseCommand):
    help = 'Seed the database with realistic sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush', action='store_true',
            help='Delete existing sample data before seeding',
        )

    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write('Flushing existing data...')
            self._flush()

        self.stdout.write('Seeding data...')
        admin = self._create_admin()
        merchants = self._create_merchants()
        skus = self._create_skus(merchants)
        promos = self._create_promos(merchants, skus)
        campaigns = self._create_campaigns(merchants, skus, promos)
        self._create_creatives(campaigns, admin)
        self._create_ab_variants(campaigns)
        conversations = self._create_conversations(merchants, campaigns)
        tokens = self._create_redirect_tokens(merchants, campaigns, skus)
        clicks = self._create_click_events(tokens)
        conversions = self._create_conversions(merchants, clicks)
        self._create_invoices(merchants, conversions)

        self.stdout.write(self.style.SUCCESS(
            f'\nSample data seeded successfully!\n'
            f'  Admin: admin / admin1234\n'
            f'  Merchants: {len(merchants)} merchants created\n'
            f'  SKUs: {len(skus)} products\n'
            f'  Campaigns: {len(campaigns)} campaigns\n'
            f'  Conversations: {len(conversations)} conversations\n'
            f'  Clicks: {len(clicks)} click events\n'
            f'  Conversions: {len(conversions)} conversions\n'
        ))

    def _flush(self):
        InvoiceLine.objects.all().delete()
        Invoice.objects.all().delete()
        ConversionEvent.objects.all().delete()
        ClickEvent.objects.all().delete()
        RedirectToken.objects.all().delete()
        Message.objects.all().delete()
        Conversation.objects.all().delete()
        ABTestVariant.objects.all().delete()
        CampaignCreative.objects.all().delete()
        Campaign.objects.all().delete()
        PromoRule.objects.all().delete()
        SKU.objects.all().delete()
        MerchantProfile.objects.all().delete()
        User.objects.filter(username__startswith='merchant').delete()
        User.objects.filter(username='admin').delete()

    def _create_admin(self):
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'role': 'admin',
                'email': 'admin@salescount.in',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            admin.set_password('admin1234')
            admin.save()
            self.stdout.write('  Created admin user: admin / admin1234')
        return admin

    def _create_merchants(self):
        merchant_data = [
            {
                'username': 'merchant_techmart',
                'company_name': 'TechMart India',
                'contact_email': 'sales@techmart.in',
                'contact_phone': '+919876543210',
                'billing_address': '42 MG Road, Bengaluru 560001',
                'commission_rate': Decimal('5.00'),
                'daily_budget_cap': Decimal('500.00'),
                'tier': MerchantProfile.Tier.GOLD,
                'whatsapp_number': '+919876543210',
            },
            {
                'username': 'merchant_fashionhub',
                'company_name': 'FashionHub',
                'contact_email': 'hello@fashionhub.in',
                'contact_phone': '+919876543211',
                'billing_address': '15 Linking Road, Mumbai 400050',
                'commission_rate': Decimal('7.50'),
                'daily_budget_cap': Decimal('800.00'),
                'tier': MerchantProfile.Tier.PLATINUM,
                'whatsapp_number': '+919876543211',
            },
            {
                'username': 'merchant_homestyle',
                'company_name': 'HomeStyle Living',
                'contact_email': 'info@homestyle.in',
                'contact_phone': '+919876543212',
                'billing_address': '88 Nehru Place, Delhi 110019',
                'commission_rate': Decimal('4.50'),
                'daily_budget_cap': Decimal('300.00'),
                'tier': MerchantProfile.Tier.SILVER,
                'whatsapp_number': '+919876543212',
            },
            {
                'username': 'merchant_healthplus',
                'company_name': 'HealthPlus Pharmacy',
                'contact_email': 'orders@healthplus.in',
                'contact_phone': '+919876543213',
                'billing_address': '5 Anna Salai, Chennai 600002',
                'commission_rate': Decimal('6.00'),
                'daily_budget_cap': Decimal('400.00'),
                'tier': MerchantProfile.Tier.BRONZE,
                'whatsapp_number': '+919876543213',
            },
        ]

        merchants = []
        for data in merchant_data:
            username = data.pop('username')
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'role': 'merchant', 'email': data['contact_email']},
            )
            if created:
                user.set_password('merchant1234')
                user.save()

            merchant, _ = MerchantProfile.objects.get_or_create(
                user=user,
                defaults={
                    **data,
                    'status': MerchantProfile.Status.APPROVED,
                    'approved_at': timezone.now() - timedelta(days=30),
                },
            )
            merchants.append(merchant)
            self.stdout.write(f'  Merchant: {merchant.company_name} ({username} / merchant1234)')

        return merchants

    def _create_skus(self, merchants):
        sku_catalog = {
            0: [  # TechMart
                ('TM-PHONE-001', 'iPhone 15 Pro 256GB', 'Smartphones', 134900, 129900, 'https://techmart.in/iphone15pro'),
                ('TM-PHONE-002', 'Samsung Galaxy S24 Ultra', 'Smartphones', 129999, 119999, 'https://techmart.in/s24ultra'),
                ('TM-LAPTOP-001', 'MacBook Air M3', 'Laptops', 114900, 109900, 'https://techmart.in/macbook-m3'),
                ('TM-AUDIO-001', 'Sony WH-1000XM5', 'Audio', 29990, 24990, 'https://techmart.in/sony-xm5'),
                ('TM-WATCH-001', 'Apple Watch Ultra 2', 'Wearables', 89900, 84900, 'https://techmart.in/watch-ultra2'),
            ],
            1: [  # FashionHub
                ('FH-SHIRT-001', 'Linen Casual Shirt', 'Men Shirts', 2499, 1999, 'https://fashionhub.in/linen-shirt'),
                ('FH-DRESS-001', 'Floral Maxi Dress', 'Women Dresses', 3999, 2999, 'https://fashionhub.in/maxi-dress'),
                ('FH-SHOE-001', 'Leather Oxford Shoes', 'Footwear', 5999, 4499, 'https://fashionhub.in/oxford'),
                ('FH-BAG-001', 'Canvas Tote Bag', 'Accessories', 1499, 999, 'https://fashionhub.in/tote'),
                ('FH-JEANS-001', 'Slim Fit Denim Jeans', 'Men Jeans', 3499, 2799, 'https://fashionhub.in/slim-jeans'),
            ],
            2: [  # HomeStyle
                ('HS-SOFA-001', 'L-Shape Sectional Sofa', 'Furniture', 45999, 39999, 'https://homestyle.in/sofa'),
                ('HS-LAMP-001', 'Nordic Floor Lamp', 'Lighting', 4999, 3999, 'https://homestyle.in/lamp'),
                ('HS-RUG-001', 'Persian Area Rug 5x7', 'Decor', 12999, 9999, 'https://homestyle.in/rug'),
                ('HS-BED-001', 'King Size Bed Frame', 'Furniture', 29999, 24999, 'https://homestyle.in/bed'),
            ],
            3: [  # HealthPlus
                ('HP-VIT-001', 'Multivitamin 90 Tablets', 'Vitamins', 999, 799, 'https://healthplus.in/multivitamin'),
                ('HP-PROT-001', 'Whey Protein 2kg', 'Nutrition', 3999, 2999, 'https://healthplus.in/whey'),
                ('HP-MASK-001', 'N95 Masks (Pack of 50)', 'Safety', 1499, 999, 'https://healthplus.in/n95'),
                ('HP-THERM-001', 'Digital Thermometer', 'Devices', 599, 499, 'https://healthplus.in/thermometer'),
            ],
        }

        all_skus = []
        for idx, merchant in enumerate(merchants):
            for code, name, category, price, disc, url in sku_catalog.get(idx, []):
                sku, _ = SKU.objects.get_or_create(
                    merchant=merchant,
                    sku_code=code,
                    defaults={
                        'name': name,
                        'description': f'High-quality {name.lower()} from {merchant.company_name}.',
                        'category': category,
                        'original_price': Decimal(str(price)),
                        'discounted_price': Decimal(str(disc)),
                        'landing_url': url,
                        'stock_quantity': random.randint(10, 500),
                        'is_active': True,
                    },
                )
                all_skus.append(sku)

        self.stdout.write(f'  Created {len(all_skus)} SKUs')
        return all_skus

    def _create_promos(self, merchants, skus):
        now = timezone.now()
        promos = []

        promo_data = [
            (merchants[0], 'TechMart Flash Sale', 'percentage', 10, 'TECH'),
            (merchants[1], 'Fashion 20% Off', 'percentage', 20, 'FASH'),
            (merchants[1], 'Free Shipping', 'free_shipping', 0, 'SHIP'),
            (merchants[2], 'HomeStyle Rs.500 Off', 'fixed', 500, 'HOME'),
            (merchants[3], 'HealthPlus 15% Discount', 'percentage', 15, 'HLTH'),
        ]

        for merchant, name, ptype, value, prefix in promo_data:
            promo, _ = PromoRule.objects.get_or_create(
                merchant=merchant,
                name=name,
                defaults={
                    'promo_type': ptype,
                    'value': Decimal(str(value)),
                    'coupon_prefix': prefix,
                    'max_uses': 100,
                    'valid_from': now - timedelta(days=7),
                    'valid_until': now + timedelta(days=60),
                    'is_active': True,
                },
            )
            # Add applicable SKUs
            merchant_skus = [s for s in skus if s.merchant_id == merchant.id]
            promo.applicable_skus.set(merchant_skus)
            promos.append(promo)

        self.stdout.write(f'  Created {len(promos)} promo rules')
        return promos

    def _create_campaigns(self, merchants, skus, promos):
        now = timezone.now()
        campaigns = []

        campaign_data = [
            (merchants[0], 'Summer Tech Sale', 'Huge discounts on electronics this summer!', 'active', -10, 30, 2000),
            (merchants[0], 'New Arrivals Launch', 'Introducing the latest tech gadgets.', 'draft', 5, 35, 500),
            (merchants[1], 'Monsoon Fashion Fest', 'Trendy styles for the rainy season.', 'active', -5, 25, 1500),
            (merchants[1], 'Wedding Season Collection', 'Exclusive wedding wear collection.', 'paused', -15, 15, 1000),
            (merchants[2], 'Home Makeover Week', 'Transform your living space.', 'active', -3, 27, 800),
            (merchants[2], 'Diwali Decor Sale', 'Festival decor at best prices.', 'ended', -45, -15, 1200),
            (merchants[3], 'Wellness Month', 'Health supplements & essentials on sale.', 'active', -7, 23, 600),
            (merchants[3], 'Immunity Booster Campaign', 'Stay healthy this winter.', 'draft', 10, 40, 400),
        ]

        promo_map = {m.id: p for m, p in zip(
            [merchants[0], merchants[1], merchants[2], merchants[3]],
            [promos[0], promos[1], promos[3], promos[4]],
        )}

        for merchant, name, desc, status, start_offset, end_offset, limit in campaign_data:
            campaign, created = Campaign.objects.get_or_create(
                merchant=merchant,
                name=name,
                defaults={
                    'description': desc,
                    'status': status,
                    'start_date': now + timedelta(days=start_offset),
                    'end_date': now + timedelta(days=end_offset),
                    'daily_message_limit': limit,
                    'messages_sent_today': random.randint(0, limit // 3) if status == 'active' else 0,
                    'promo_rule': promo_map.get(merchant.id),
                },
            )
            # Assign target SKUs
            if created:
                merchant_skus = [s for s in skus if s.merchant_id == merchant.id]
                campaign.target_skus.set(merchant_skus[:3])
            campaigns.append(campaign)

        self.stdout.write(f'  Created {len(campaigns)} campaigns')
        return campaigns

    def _create_creatives(self, campaigns, admin):
        for campaign in campaigns:
            if CampaignCreative.objects.filter(campaign=campaign).exists():
                continue

            CampaignCreative.objects.create(
                campaign=campaign,
                name=f'{campaign.name} - Default',
                greeting_template=(
                    f"Hi {{{{customer_name}}}}! Welcome to {campaign.merchant.company_name}. "
                    f"We have exciting offers just for you!"
                ),
                pitch_template=(
                    f"Check out our {campaign.name} deals! "
                    f"{{{{product_name}}}} is now available at a special price of {{{{discounted_price}}}}. "
                    f"That's {{{{discount_percent}}}}% off!"
                ),
                close_template=(
                    "Ready to grab this deal? Click here: {{{{tracking_url}}}}\n"
                    "Use code {{{{coupon_code}}}} for extra savings!"
                ),
                is_approved=campaign.status in ('active', 'paused', 'ended'),
                approved_by=admin if campaign.status in ('active', 'paused', 'ended') else None,
            )

        self.stdout.write(f'  Created creatives for {len(campaigns)} campaigns')

    def _create_ab_variants(self, campaigns):
        active_campaigns = [c for c in campaigns if c.status in ('active', 'paused')]
        for campaign in active_campaigns:
            if ABTestVariant.objects.filter(campaign=campaign).exists():
                continue

            ABTestVariant.objects.create(
                campaign=campaign,
                name='Control',
                variant_type='message_tone',
                config_json={'tone': 'friendly', 'urgency': 'low'},
                traffic_weight=0.5,
                impressions=random.randint(100, 1000),
                conversions=random.randint(5, 50),
            )
            ABTestVariant.objects.create(
                campaign=campaign,
                name='Urgent Tone',
                variant_type='message_tone',
                config_json={'tone': 'urgent', 'urgency': 'high'},
                traffic_weight=0.5,
                impressions=random.randint(100, 1000),
                conversions=random.randint(5, 50),
            )

        self.stdout.write(f'  Created A/B variants for {len(active_campaigns)} campaigns')

    def _create_conversations(self, merchants, campaigns):
        conversations = []
        stages = ['greeting', 'qualifying', 'narrowing', 'pitching', 'objection_handling', 'closing', 'ended']

        active_campaigns = [c for c in campaigns if c.status in ('active', 'paused', 'ended')]

        for campaign in active_campaigns:
            num_convos = random.randint(8, 20)
            for i in range(num_convos):
                phone = f'+9198{random.randint(10000000, 99999999)}'
                stage = random.choice(stages)

                convo, created = Conversation.objects.get_or_create(
                    merchant=campaign.merchant,
                    phone_number=phone,
                    campaign=campaign,
                    defaults={
                        'stage': stage,
                    },
                )
                if created:
                    conversations.append(convo)
                    # Add some messages
                    msg_count = random.randint(2, 8)
                    for j in range(msg_count):
                        direction = 'inbound' if j % 2 == 0 else 'outbound'
                        Message.objects.create(
                            conversation=convo,
                            direction=direction,
                            body=f'Sample {"customer" if direction == "inbound" else "bot"} message #{j+1}',
                            stage_at_send=convo.stage,
                        )

        self.stdout.write(f'  Created {len(conversations)} conversations with messages')
        return conversations

    def _create_redirect_tokens(self, merchants, campaigns, skus):
        now = timezone.now()
        tokens = []

        active_campaigns = [c for c in campaigns if c.status in ('active', 'paused', 'ended')]

        for campaign in active_campaigns:
            merchant_skus = [s for s in skus if s.merchant_id == campaign.merchant_id]
            if not merchant_skus:
                continue

            conversation = Conversation.objects.filter(
                merchant=campaign.merchant,
                campaign=campaign,
            ).first()
            if not conversation:
                # Fallback: create a conversation so redirect tokens have a valid FK
                phone = f'+9198{random.randint(10000000, 99999999)}'
                conversation = Conversation.objects.create(
                    phone_number=phone,
                    merchant=campaign.merchant,
                    campaign=campaign,
                )

            num_tokens = random.randint(10, 30)
            for _ in range(num_tokens):
                sku = random.choice(merchant_skus)
                token = RedirectToken.objects.create(
                    conversation=conversation,
                    merchant=campaign.merchant,
                    campaign=campaign,
                    sku=sku,
                    destination_url=sku.landing_url,
                    expires_at=now + timedelta(hours=72),
                )
                tokens.append(token)

        self.stdout.write(f'  Created {len(tokens)} redirect tokens')
        return tokens

    def _create_click_events(self, tokens):
        now = timezone.now()
        clicks = []
        user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)',
            'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)',
        ]

        for token in tokens:
            # 70% chance of at least one click
            if random.random() > 0.3:
                num_clicks = random.randint(1, 3)
                for _ in range(num_clicks):
                    is_fraud = random.random() < 0.08  # 8% fraud rate
                    click = ClickEvent.objects.create(
                        redirect_token=token,
                        ip_address=f'{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}',
                        user_agent=random.choice(user_agents),
                        referer='https://wa.me/',
                        clicked_at=now - timedelta(
                            days=random.randint(0, 14),
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59),
                        ),
                        is_fraudulent=is_fraud,
                        fraud_score=random.uniform(0.7, 1.0) if is_fraud else random.uniform(0.0, 0.3),
                    )
                    clicks.append(click)

        self.stdout.write(f'  Created {len(clicks)} click events ({sum(1 for c in clicks if c.is_fraudulent)} fraudulent)')
        return clicks

    def _create_conversions(self, merchants, clicks):
        conversions = []
        valid_clicks = [c for c in clicks if not c.is_fraudulent]

        # ~25% of valid clicks convert
        converting_clicks = random.sample(valid_clicks, min(len(valid_clicks), len(valid_clicks) // 4 + 1))

        for click in converting_clicks:
            token = click.redirect_token
            merchant = token.merchant
            order_amount = Decimal(str(random.randint(500, 15000)))
            commission = (order_amount * merchant.commission_rate / 100).quantize(Decimal('0.01'))

            conv = ConversionEvent.objects.create(
                merchant=merchant,
                click_event=click,
                order_id=f'ORD-{random.randint(100000, 999999)}',
                order_amount=order_amount,
                commission_amount=commission,
                converted_at=click.clicked_at + timedelta(minutes=random.randint(5, 120)),
                is_valid=True,
                is_disputed=False,
            )
            conversions.append(conv)

        self.stdout.write(f'  Created {len(conversions)} conversions')
        return conversions

    def _create_invoices(self, merchants, conversions):
        now = timezone.now()
        invoices_created = 0

        for merchant in merchants:
            merchant_convs = [c for c in conversions if c.merchant_id == merchant.id]
            if not merchant_convs:
                continue

            total = sum(c.commission_amount for c in merchant_convs)
            invoice_number = f'SC-{merchant.id}-{now.strftime("%Y%m%d")}'

            if Invoice.objects.filter(invoice_number=invoice_number).exists():
                continue

            invoice = Invoice.objects.create(
                merchant=merchant,
                invoice_number=invoice_number,
                period_start=(now - timedelta(days=7)).date(),
                period_end=(now - timedelta(days=1)).date(),
                total_conversions=len(merchant_convs),
                subtotal=total,
                total=total,
                due_date=(now + timedelta(days=30)).date(),
                status=random.choice(['draft', 'sent', 'paid']),
            )

            for conv in merchant_convs:
                InvoiceLine.objects.create(
                    invoice=invoice,
                    conversion_event=conv,
                    description=f'Conversion {conv.order_id}',
                    billing_type='cpa',
                    quantity=1,
                    unit_price=conv.commission_amount,
                    line_total=conv.commission_amount,
                )

            invoices_created += 1

        self.stdout.write(f'  Created {invoices_created} invoices with line items')
