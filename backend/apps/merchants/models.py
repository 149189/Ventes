import secrets

from django.conf import settings
from django.db import models


class MerchantProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        SUSPENDED = 'suspended', 'Suspended'

    class Tier(models.TextChoices):
        BRONZE = 'bronze', 'Bronze'
        SILVER = 'silver', 'Silver'
        GOLD = 'gold', 'Gold'
        PLATINUM = 'platinum', 'Platinum'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='merchant_profile',
    )
    company_name = models.CharField(max_length=255)
    company_website = models.URLField(blank=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    billing_address = models.TextField()
    tax_id = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.BRONZE)

    # Billing settings
    commission_rate = models.DecimalField(max_digits=4, decimal_places=2, default=5.00)
    auto_optimize_commission = models.BooleanField(default=False)
    daily_budget_cap = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    billing_model = models.CharField(
        max_length=10, choices=[('cpa', 'CPA'), ('cpc', 'CPC')], default='cpa',
    )
    dispute_window_days = models.IntegerField(default=14)

    # Razorpay
    razorpay_customer_id = models.CharField(max_length=255, blank=True)

    # HMAC secret for postbacks
    hmac_secret = models.CharField(max_length=64, default=secrets.token_hex)

    # WhatsApp
    whatsapp_number = models.CharField(max_length=20, blank=True)

    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'merchant_profiles'

    def __str__(self):
        return self.company_name


class SKU(models.Model):
    merchant = models.ForeignKey(MerchantProfile, on_delete=models.CASCADE, related_name='skus')
    sku_code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    landing_url = models.URLField()
    image_url = models.URLField(blank=True)
    stock_quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    pinecone_vector_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'skus'
        unique_together = ('merchant', 'sku_code')

    def __str__(self):
        return f"{self.sku_code} - {self.name}"


class PromoRule(models.Model):
    class PromoType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        FIXED_AMOUNT = 'fixed', 'Fixed Amount'
        FREE_SHIPPING = 'free_shipping', 'Free Shipping'

    merchant = models.ForeignKey(MerchantProfile, on_delete=models.CASCADE, related_name='promo_rules')
    name = models.CharField(max_length=100)
    promo_type = models.CharField(max_length=20, choices=PromoType.choices)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    coupon_prefix = models.CharField(max_length=20)
    max_uses = models.IntegerField(default=0)
    uses_count = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    applicable_skus = models.ManyToManyField(SKU, blank=True, related_name='promo_rules')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promo_rules'

    def __str__(self):
        return f"{self.name} ({self.get_promo_type_display()})"
