"""Seed the database with development data."""
import os
import sys
import django

# Set up Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salescount.settings.dev')
django.setup()

from django.contrib.auth import get_user_model
from apps.merchants.models import MerchantProfile, SKU, PromoRule
from apps.campaigns.models import Campaign
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


def seed():
    print("Seeding database...")

    # Create admin user
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@salescount.com',
            'role': 'admin',
            'is_staff': True,
            'is_superuser': True,
            'is_verified': True,
        },
    )
    if created:
        admin.set_password('admin123')
        admin.save()
        print("Created admin user (admin/admin123)")

    # Create merchant user
    merchant_user, created = User.objects.get_or_create(
        username='merchant1',
        defaults={
            'email': 'merchant@example.com',
            'role': 'merchant',
            'phone': '+919876543210',
            'is_verified': True,
        },
    )
    if created:
        merchant_user.set_password('merchant123')
        merchant_user.save()
        print("Created merchant user (merchant1/merchant123)")

    # Create merchant profile
    merchant, _ = MerchantProfile.objects.get_or_create(
        user=merchant_user,
        defaults={
            'company_name': 'Demo Fashion Store',
            'company_website': 'https://demofashion.example.com',
            'contact_email': 'merchant@example.com',
            'contact_phone': '+919876543210',
            'billing_address': '123 Market Street, Mumbai 400001',
            'status': 'approved',
            'commission_rate': 6.00,
            'daily_budget_cap': 500.00,
            'whatsapp_number': 'whatsapp:+919876543210',
            'approved_at': timezone.now(),
        },
    )
    print(f"Merchant profile: {merchant.company_name}")

    # Create SKUs
    skus_data = [
        {
            'sku_code': 'DF-TSHIRT-001',
            'name': 'Classic Cotton T-Shirt',
            'description': 'Premium 100% cotton t-shirt, available in 6 colors. Breathable fabric, perfect for daily wear.',
            'category': 'T-Shirts',
            'original_price': 29.99,
            'discounted_price': 19.99,
            'landing_url': 'https://demofashion.example.com/tshirt-001',
            'stock_quantity': 150,
        },
        {
            'sku_code': 'DF-JEANS-001',
            'name': 'Slim Fit Denim Jeans',
            'description': 'Stretch denim jeans with modern slim fit. Dark wash, 5-pocket design.',
            'category': 'Jeans',
            'original_price': 59.99,
            'discounted_price': 44.99,
            'landing_url': 'https://demofashion.example.com/jeans-001',
            'stock_quantity': 75,
        },
        {
            'sku_code': 'DF-SNEAKER-001',
            'name': 'Urban Runner Sneakers',
            'description': 'Lightweight running sneakers with memory foam insole. Available in 4 colors.',
            'category': 'Footwear',
            'original_price': 89.99,
            'discounted_price': 69.99,
            'landing_url': 'https://demofashion.example.com/sneaker-001',
            'stock_quantity': 5,  # Low stock for scarcity signal
        },
        {
            'sku_code': 'DF-JACKET-001',
            'name': 'Bomber Jacket',
            'description': 'Stylish bomber jacket with zip-up front. Water-resistant outer shell.',
            'category': 'Outerwear',
            'original_price': 119.99,
            'landing_url': 'https://demofashion.example.com/jacket-001',
            'stock_quantity': 30,
        },
    ]

    for sku_data in skus_data:
        sku, created = SKU.objects.get_or_create(
            merchant=merchant,
            sku_code=sku_data['sku_code'],
            defaults=sku_data,
        )
        if created:
            print(f"  Created SKU: {sku.name}")

    # Create promo rule
    promo, _ = PromoRule.objects.get_or_create(
        merchant=merchant,
        name='Launch Discount',
        defaults={
            'promo_type': 'percentage',
            'value': 10,
            'coupon_prefix': 'SC',
            'max_uses': 1000,
            'valid_from': timezone.now(),
            'valid_until': timezone.now() + timedelta(days=30),
        },
    )
    print(f"Promo rule: {promo.name}")

    # Create campaign
    campaign, created = Campaign.objects.get_or_create(
        merchant=merchant,
        name='Summer Sale 2025',
        defaults={
            'description': 'Summer collection sale with up to 30% off',
            'status': 'active',
            'promo_rule': promo,
            'start_date': timezone.now(),
            'end_date': timezone.now() + timedelta(days=30),
            'daily_message_limit': 500,
        },
    )
    if created:
        campaign.target_skus.set(SKU.objects.filter(merchant=merchant))
        print(f"Campaign: {campaign.name}")

    print("\nSeeding complete!")


if __name__ == '__main__':
    seed()
