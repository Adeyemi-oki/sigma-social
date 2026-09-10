"""
Shared image-upload validation, used by both profile pictures and
post images.

Django's ImageField already verifies -- via Pillow -- that an
uploaded file truly decodes as an image, and rejects it otherwise;
that alone stops a renamed .exe/.php file from being accepted as a
"profile_picture.jpg". This module adds the two checks Django doesn't
apply for us: a sane file-size ceiling and a matching file extension,
so uploads fail fast with a friendly message before ever touching
storage.
"""

from django.core.exceptions import ValidationError

MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "gif", "webp")


def validate_image_upload(uploaded_file):
    if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError("Image must be smaller than 5MB.")

    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Unsupported file type. Please upload a JPG, PNG, GIF, or WEBP image.")
