from django.urls import path, include

from rest_framework.routers import DefaultRouter

from apps.accounts.permission_management.api.views import GroupViewSet, PermissionViewSet
from apps.accounts.user.api.views import (
    CustomUserViewSet,
    UserLoginAPIView,
    TokenRefreshView,
    UserLogoutView,
    VerifyToken,
)


router = DefaultRouter()
router.register(r"users", CustomUserViewSet, basename="user")
router.register(r"permissions", PermissionViewSet, basename="permission")
router.register(r"groups", GroupViewSet, basename="group")


urlpatterns = [
    path("auth/login/", UserLoginAPIView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("auth/logout/", UserLogoutView.as_view(), name="logout"),
    path("auth/verify/", VerifyToken.as_view()),
    # path("permissions/", PermissionViewSet.as_view()),
    path("", include(router.urls)),
]
