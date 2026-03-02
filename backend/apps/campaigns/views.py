from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsAdmin, IsAdminOrMerchant
from .models import Campaign, CampaignCreative, ABTestVariant
from .serializers import CampaignSerializer, CampaignCreativeSerializer, ABTestVariantSerializer


class CampaignViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Campaign.objects.all()
        return Campaign.objects.filter(merchant=user.merchant_profile)

    def perform_create(self, serializer):
        serializer.save(merchant=self.request.user.merchant_profile)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = Campaign.Status.ACTIVE
        campaign.save()
        return Response(self.get_serializer(campaign).data)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = Campaign.Status.PAUSED
        campaign.save()
        return Response(self.get_serializer(campaign).data)


class CampaignCreativeViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignCreativeSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)

    def get_queryset(self):
        return CampaignCreative.objects.filter(campaign_id=self.kwargs['campaign_pk'])

    def perform_create(self, serializer):
        serializer.save(campaign_id=self.kwargs['campaign_pk'])


class ABTestVariantViewSet(viewsets.ModelViewSet):
    serializer_class = ABTestVariantSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)

    def get_queryset(self):
        return ABTestVariant.objects.filter(campaign_id=self.kwargs['campaign_pk'])

    def perform_create(self, serializer):
        serializer.save(campaign_id=self.kwargs['campaign_pk'])


class AdminCreativeApprovalView(viewsets.GenericViewSet):
    serializer_class = CampaignCreativeSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    queryset = CampaignCreative.objects.all()

    @action(detail=True, methods=['put'])
    def approve(self, request, pk=None):
        creative = self.get_object()
        creative.is_approved = True
        creative.approved_by = request.user
        creative.save()
        return Response(self.get_serializer(creative).data)

    @action(detail=True, methods=['put'])
    def reject(self, request, pk=None):
        creative = self.get_object()
        creative.is_approved = False
        creative.save()
        return Response(self.get_serializer(creative).data)
