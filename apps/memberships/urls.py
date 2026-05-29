from django.urls import path, include

from rest_framework.routers import DefaultRouter

from apps.memberships.invitation.api.views import InvitationViewSet
from apps.memberships.membership.api.views import MembershipViewSet



router = DefaultRouter()

router.register(r"memberships", MembershipViewSet, basename="membership")
router.register(r"invitations", InvitationViewSet, basename="invitation")

urlpatterns = [
    # path("invite/", InviteMemberView.as_view()),
    # path("accept/", AcceptInvitationView.as_view()),
    path("", include(router.urls)),
]
