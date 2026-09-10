from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import RegisterForm


def register(request):
    """
    Handle new account creation using Django's built-in UserCreationForm.

    Django takes care of hashing the password (via form.save()) and
    validating uniqueness/strength -- we never touch raw passwords here.
    """
    # Logged-in users don't need to register again.
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()  # hashes the password and creates the User row
            messages.success(request, "Account created successfully. Please log in.")
            return redirect("login")
        # Invalid form: fall through and re-render with field errors attached.
    else:
        form = RegisterForm()

    return render(request, "users/register.html", {"form": form})


class SigmaLoginView(LoginView):
    """
    Thin wrapper around Django's built-in LoginView.

    LoginView already handles:
    - authenticating the submitted username/password
    - creating the session on success
    - showing a form error on invalid credentials
    - redirecting to LOGIN_REDIRECT_URL on success

    We only point it at our own template.
    """

    template_name = "users/login.html"
    redirect_authenticated_user = True


@require_POST
def logout(request):
    """
    Log the current user out.

    POST-only: logging out changes state (destroys the session), so it
    should never be triggerable by a plain GET link or link prefetch.
    """
    auth_logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")
