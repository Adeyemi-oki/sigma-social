from django import forms

from image_validators import validate_image_upload

from .models import Comment, Post


class PostForm(forms.ModelForm):
    """
    Form for creating a post.

    Deliberately excludes `author` -- the author is never taken from
    submitted form data; the view always assigns it from
    `request.user` on the server.
    """

    class Meta:
        model = Post
        fields = ("content", "image")
        widgets = {
            "content": forms.Textarea(
                attrs={"rows": 4, "placeholder": "What's on your mind?"}
            ),
        }
        labels = {
            "content": "",
            "image": "Image (optional)",
        }

    def clean_content(self):
        # Trim whitespace early so "   " alone can't slip past the
        # "must have content or an image" check as if it were real text.
        return self.cleaned_data.get("content", "").strip()

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "content_type"):
            validate_image_upload(image)
        return image

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content", "")
        image = cleaned_data.get("image")
        if not content and not image:
            raise forms.ValidationError("Write something or attach an image before posting.")
        return cleaned_data


class CommentForm(forms.ModelForm):
    """
    Form for creating a comment.

    Deliberately excludes `post` and `author` -- which post a comment
    belongs to is always taken from the URL, and the author is always
    `request.user`. Neither can be influenced by submitted form data.
    """

    class Meta:
        model = Comment
        fields = ("content",)
        widgets = {
            "content": forms.Textarea(
                attrs={"rows": 2, "placeholder": "Write a comment..."}
            ),
        }
        labels = {"content": ""}

    def clean_content(self):
        content = self.cleaned_data.get("content", "").strip()
        if not content:
            raise forms.ValidationError("Comment can't be empty.")
        return content
