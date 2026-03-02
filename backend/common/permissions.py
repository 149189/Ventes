from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsMerchant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'merchant'


class IsAgent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'agent'


class IsAdminOrMerchant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('admin', 'merchant')
