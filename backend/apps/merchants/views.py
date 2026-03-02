import csv
import io

from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from common.permissions import IsMerchant, IsAdmin
from .models import MerchantProfile, SKU, PromoRule
from .serializers import (
    MerchantProfileSerializer,
    MerchantOnboardSerializer,
    BillingSettingsSerializer,
    SKUSerializer,
    PromoRuleSerializer,
)


class MerchantProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = MerchantProfileSerializer
    permission_classes = (permissions.IsAuthenticated, IsMerchant)

    def get_object(self):
        profile, _ = MerchantProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'contact_email': self.request.user.email,
                'company_name': '',
                'contact_phone': '',
                'billing_address': '',
            },
        )
        return profile


class MerchantOnboardView(generics.CreateAPIView):
    serializer_class = MerchantOnboardSerializer
    permission_classes = (permissions.IsAuthenticated, IsMerchant)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BillingSettingsView(generics.UpdateAPIView):
    serializer_class = BillingSettingsSerializer
    permission_classes = (permissions.IsAuthenticated, IsMerchant)

    def get_object(self):
        return self.request.user.merchant_profile


class SKUViewSet(viewsets.ModelViewSet):
    serializer_class = SKUSerializer
    permission_classes = (permissions.IsAuthenticated, IsMerchant)

    def get_queryset(self):
        return SKU.objects.filter(merchant=self.request.user.merchant_profile)

    def perform_create(self, serializer):
        serializer.save(merchant=self.request.user.merchant_profile)

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def upload(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        decoded = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        created = 0
        errors = []

        for i, row in enumerate(reader, start=2):
            try:
                SKU.objects.update_or_create(
                    merchant=request.user.merchant_profile,
                    sku_code=row['sku_code'],
                    defaults={
                        'name': row['name'],
                        'description': row.get('description', ''),
                        'category': row.get('category', ''),
                        'original_price': row['original_price'],
                        'discounted_price': row.get('discounted_price') or None,
                        'landing_url': row['landing_url'],
                        'image_url': row.get('image_url', ''),
                        'stock_quantity': int(row.get('stock_quantity', 0)),
                    },
                )
                created += 1
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

        return Response({
            'created': created,
            'errors': errors,
        }, status=status.HTTP_201_CREATED)


class PromoRuleViewSet(viewsets.ModelViewSet):
    serializer_class = PromoRuleSerializer
    permission_classes = (permissions.IsAuthenticated, IsMerchant)

    def get_queryset(self):
        return PromoRule.objects.filter(merchant=self.request.user.merchant_profile)

    def perform_create(self, serializer):
        serializer.save(merchant=self.request.user.merchant_profile)


# Admin views
class AdminMerchantListView(generics.ListAPIView):
    serializer_class = MerchantProfileSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    queryset = MerchantProfile.objects.all()
    filterset_fields = ('status', 'tier')
    search_fields = ('company_name', 'contact_email')
    ordering_fields = ('created_at', 'company_name')


class AdminMerchantActionView(generics.UpdateAPIView):
    serializer_class = MerchantProfileSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    queryset = MerchantProfile.objects.all()

    def update(self, request, *args, **kwargs):
        merchant = self.get_object()
        action_type = kwargs.get('action_type')

        from django.utils import timezone

        if action_type == 'approve':
            merchant.status = MerchantProfile.Status.APPROVED
            merchant.approved_at = timezone.now()
        elif action_type == 'reject':
            merchant.status = MerchantProfile.Status.REJECTED
        elif action_type == 'suspend':
            merchant.status = MerchantProfile.Status.SUSPENDED
        else:
            return Response({'error': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)

        merchant.save()
        return Response(self.get_serializer(merchant).data)
