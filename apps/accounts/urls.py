from django.urls import path, include

from rest_framework.routers import DefaultRouter

from apps.accounts.user.api.views import (
    CustomUserViewSet,
    UserLoginAPIView,
    TokenRefreshView,
    UserLogoutView,
    VerifyToken,
)


router = DefaultRouter()
router.register(r"users", CustomUserViewSet, basename="user")


urlpatterns = [
    path("auth/login/", UserLoginAPIView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("auth/logout/", UserLogoutView.as_view(), name="logout"),
    path("auth/verify/", VerifyToken.as_view()),
    path("", include(router.urls)),
]
