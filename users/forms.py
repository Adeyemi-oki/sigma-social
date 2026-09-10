from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    """
    Registration form based on Django's built-in UserCreationForm.

    UserCreationForm already handles:
    - username uniqueness validation
    - password confirmation matching
    - running Django's configured password validators
    - hashing the password before saving (it never stores plain text)

    We only customise it to use the default User model explicitly and
    to make sure error messages render cleanly in our template.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)
