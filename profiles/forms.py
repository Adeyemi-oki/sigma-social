from django import forms

from image_validators import validate_image_upload

from .models import Profile


class ProfileEditForm(forms.ModelForm):
    """
    Lets a user update their own bio and profile picture.

    Deliberately excludes `user` — the owner of a profile is never
    editable through this form, only set once at creation time.
    """

    class Meta:
        model = Profile
        fields = ("profile_picture", "bio")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3, "maxlength": 280}),
        }

    def clean_profile_picture(self):
        picture = self.cleaned_data.get("profile_picture")
        # FieldFile (an already-saved picture, unchanged this submission)
        # has no .size check needed here; only validate a genuinely new
        # upload (an InMemoryUploadedFile/TemporaryUploadedFile).
        if picture and hasattr(picture, "content_type"):
            validate_image_upload(picture)
        return picture
