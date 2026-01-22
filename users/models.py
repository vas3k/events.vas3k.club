from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.text import slugify

from utils.strings import random_string


class UserAccountManager(BaseUserManager):
    def create_superuser(self, username, email, password, **other_fields):
        other_fields.setdefault("is_staff", True)
        other_fields.setdefault("is_superuser", True)
        user = self.create_user(
            slug=slugify(username),
            full_name=username,
            email=email,
            password=password,
            **other_fields
        )
        user.set_password(password)
        user.save()
        return user

    def create_user(self, username, email, password=None, **other_fields):
        if not email:
            raise ValueError("Email address is required!")

        email = self.normalize_email(email)
        if password is not None:
            user = self.model(
                slug=username,
                email=email,
                password=password,
                **other_fields
            )
            user.save()
        else:
            user = self.model(
                slug=username,
                email=email,
                password=password,
                **other_fields
            )
            user.set_unusable_password()
            user.save()

        return user


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_ADMIN = "admin"
    ROLES = (
        (ROLE_ADMIN, ROLE_ADMIN),
    )

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    slug = models.CharField(max_length=32, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=128, null=True)
    avatar = models.URLField(null=True, blank=True)
    secret_hash = models.CharField(max_length=24, unique=True)

    city = models.CharField(max_length=128, null=True)
    country = models.CharField(max_length=128, null=True)
    company = models.TextField(null=True)
    position = models.TextField(null=True)
    bio = models.TextField(null=True)
    membership_started_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity_at = models.DateTimeField(auto_now=True)

    telegram_id = models.CharField(max_length=64, db_index=True, null=True, blank=True)

    roles = ArrayField(models.CharField(max_length=32, choices=ROLES), default=list, null=False)

    is_banned_on_events = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)

    objects = UserAccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["slug"]

    class Meta:
        db_table = "users"

    def save(self, *args, **kwargs):
        if not self.secret_hash:
            self.secret_hash = random_string(length=18)

        self.updated_at = datetime.utcnow()
        self.last_activity_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def get_avatar(self):
        return self.avatar or settings.DEFAULT_AVATAR

    def profile_url(self):
        return f"{settings.CLUB_BASE_URL}/user/{self.slug}/"

    def membership_created_days(self):
        if self.membership_started_at:
            return (datetime.utcnow() - self.membership_started_at).days
        return 0

    @property
    def is_admin(self):
        return self.ROLE_ADMIN in self.roles
