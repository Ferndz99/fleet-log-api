from django.db import transaction
from django.contrib.auth import get_user_model

User = get_user_model()


class UserRegistrationService:
    @classmethod
    @transaction.atomic
    def get_or_create_user(
        cls, *, email: str, password: str, is_staff: bool = False
    ) -> User:
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"is_active": True, "is_staff": is_staff},
        )

        user.set_password(password)
        user.save(update_fields=["password"])

        return user
