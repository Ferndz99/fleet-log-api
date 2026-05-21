from django.db import transaction
from django.contrib.auth import get_user_model

User = get_user_model()


class UserRegistrationService:
    @classmethod
    @transaction.atomic
    def get_or_create_user(
        cls,
        *,
        email: str,
        password: str,
    ) -> User:
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"is_active": True},
        )

        user.set_password(password)
        user.save(update_fields=["password"])

        return user
