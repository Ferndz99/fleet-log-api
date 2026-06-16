# apps/accounts/profile/domain/services.py

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.accounts.profile.domain.models import Profile

User = get_user_model()


class ProfileService:
    @staticmethod
    def create_profile(
        user: User,
        *,
        first_name: str = "",
        last_name: str = "",
        second_last_name: str = "",
        rut: str | None = None,
        phone: str = "",
        birth_date=None,
        avatar=None,
        address: str = "",
    ) -> Profile:

        data = {
            "first_name": first_name,
            "last_name": last_name,
            "second_last_name": second_last_name,
            "rut": rut,
            "phone": phone,
            "birth_date": birth_date,
            "address": address,
        }

        if avatar is not None:
            data["avatar"] = avatar

        return Profile.objects.create(user=user, **data)

    @staticmethod
    def update_profile(
        user: User,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        second_last_name: str | None = None,
        rut: str | None = None,
        phone: str | None = None,
        birth_date=None,
        avatar=None,
        address: str | None = None,
    ) -> Profile:
        profile = Profile.objects.get(user=user)

        fields_to_update = []

        if first_name is not None:
            profile.first_name = first_name
            fields_to_update.append("first_name")

        if last_name is not None:
            profile.last_name = last_name
            fields_to_update.append("last_name")

        if second_last_name is not None:
            profile.second_last_name = second_last_name
            fields_to_update.append("second_last_name")

        if rut is not None:
            profile.rut = rut
            fields_to_update.append("rut")

        if phone is not None:
            profile.phone = phone
            fields_to_update.append("phone")

        if birth_date is not None:
            profile.birth_date = birth_date
            fields_to_update.append("birth_date")

        if avatar is not None:
            profile.avatar = avatar
            fields_to_update.append("avatar")

        if address is not None:
            profile.address = address
            fields_to_update.append("address")

        if fields_to_update:
            profile.save(update_fields=fields_to_update)

        return profile

    @staticmethod
    def get_profile(user: User) -> Profile:
        return Profile.objects.get(user=user)
