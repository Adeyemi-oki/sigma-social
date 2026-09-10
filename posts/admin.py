from django.contrib import admin

from .models import Comment, Like, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "short_content", "has_image", "created_at")
    list_filter = ("created_at",)
    search_fields = ("author__username", "content")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"

    @admin.display(description="Content")
    def short_content(self, obj):
        return (obj.content[:50] + "...") if len(obj.content) > 50 else (obj.content or "(no text)")

    @admin.display(boolean=True, description="Image")
    def has_image(self, obj):
        return bool(obj.image)


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "post", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "post__content")
    readonly_fields = ("created_at",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "post", "short_content", "created_at")
    list_filter = ("created_at",)
    search_fields = ("author__username", "content", "post__content")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"

    @admin.display(description="Content")
    def short_content(self, obj):
        return (obj.content[:50] + "...") if len(obj.content) > 50 else obj.content
