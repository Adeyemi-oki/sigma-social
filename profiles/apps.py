from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "profiles"

    def ready(self):
        # Connect the post_save signal that auto-creates a Profile
        # whenever a User is created (see profiles/signals.py).
        import profiles.signals  # noqa: F401
