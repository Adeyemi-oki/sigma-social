import io

from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .models import Comment, Like, Post


def make_test_image(name="test.png"):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="green").save(buf, format="PNG")
    buf.seek(0)
    buf.name = name
    return buf


class PostCreationTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")

    def test_authenticated_user_can_create_text_post(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(reverse("create_post"), {"content": "Hello world"}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Post.objects.filter(author=self.alice, content="Hello world").exists())

    def test_authenticated_user_can_create_image_post(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(
            reverse("create_post"),
            {"content": "", "image": make_test_image()},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        post = Post.objects.get(author=self.alice)
        self.assertTrue(bool(post.image))
        self.assertEqual(post.content, "")

    def test_authenticated_user_can_create_text_and_image_post(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(
            reverse("create_post"),
            {"content": "Look at this", "image": make_test_image()},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        post = Post.objects.get(author=self.alice)
        self.assertEqual(post.content, "Look at this")
        self.assertTrue(bool(post.image))

    def test_empty_post_is_rejected(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(reverse("create_post"), {"content": ""})
        self.assertEqual(resp.status_code, 200)  # re-renders form with errors
        self.assertFalse(Post.objects.filter(author=self.alice).exists())

    def test_whitespace_only_post_is_rejected(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(reverse("create_post"), {"content": "     "})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Post.objects.filter(author=self.alice).exists())

    def test_anonymous_user_cannot_create_post(self):
        resp = self.client.post(reverse("create_post"), {"content": "Sneaky post"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)
        self.assertFalse(Post.objects.filter(content="Sneaky post").exists())

    def test_author_is_always_the_logged_in_user(self):
        """The author cannot be overridden by anything submitted in the form."""
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(
            reverse("create_post"),
            {"content": "Trying to spoof author", "author": self.bob.pk},
        )
        post = Post.objects.get(content="Trying to spoof author")
        self.assertEqual(post.author, self.alice)
        self.assertNotEqual(post.author, self.bob)


class FeedTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")

    def test_posts_appear_in_feed(self):
        Post.objects.create(author=self.alice, content="First post")
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "First post")

    def test_feed_orders_newest_first(self):
        older = Post.objects.create(author=self.alice, content="Older")
        newer = Post.objects.create(author=self.alice, content="Newer")
        posts = list(Post.objects.all())
        self.assertEqual(posts[0], newer)
        self.assertEqual(posts[1], older)

    def test_pagination_splits_across_pages(self):
        for i in range(15):
            Post.objects.create(author=self.alice, content=f"Post {i}")
        self.client.login(username="alice", password="pw12345!")

        resp_page_1 = self.client.get(reverse("home"))
        self.assertEqual(resp_page_1.context["page_obj"].paginator.num_pages, 2)
        self.assertEqual(len(resp_page_1.context["page_obj"]), 10)

        resp_page_2 = self.client.get(reverse("home") + "?page=2")
        self.assertEqual(len(resp_page_2.context["page_obj"]), 5)


class PostDetailTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Detail test post")

    def test_post_detail_renders(self):
        resp = self.client.get(reverse("post_detail", kwargs={"pk": self.post.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Detail test post")
        self.assertContains(resp, "@alice")

    def test_unknown_post_returns_404(self):
        resp = self.client.get(reverse("post_detail", kwargs={"pk": 99999}))
        self.assertEqual(resp.status_code, 404)


class PostDeleteTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Alice's post")

    def test_author_can_delete_own_post(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(reverse("delete_post", kwargs={"pk": self.post.pk}), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_other_user_cannot_delete_post(self):
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.post(reverse("delete_post", kwargs={"pk": self.post.pk}))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_anonymous_user_cannot_delete_post(self):
        resp = self.client.post(reverse("delete_post", kwargs={"pk": self.post.pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_delete_requires_post_not_get(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("delete_post", kwargs={"pk": self.post.pk}))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())


class ProfilePostIntegrationTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        Post.objects.create(author=self.alice, content="Alice post 1")
        Post.objects.create(author=self.bob, content="Bob post 1")

    def test_profile_shows_only_that_users_posts(self):
        resp = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertContains(resp, "Alice post 1")
        self.assertNotContains(resp, "Bob post 1")

    def test_other_profile_not_polluted(self):
        resp = self.client.get(reverse("profile", kwargs={"username": "bob"}))
        self.assertContains(resp, "Bob post 1")
        self.assertNotContains(resp, "Alice post 1")


class RegressionTests(TestCase):
    """Confirm Phases 2 and 3 still work after Phase 4 changes."""

    def test_registration_still_works(self):
        resp = self.client.post(
            reverse("register"),
            {"username": "carol", "password1": "SigmaPass!2026", "password2": "SigmaPass!2026"},
        )
        self.assertRedirects(resp, reverse("login"))
        self.assertTrue(User.objects.filter(username="carol").exists())

    def test_login_and_logout_still_work(self):
        User.objects.create_user(username="dave", password="SigmaPass!2026")
        resp = self.client.post(reverse("login"), {"username": "dave", "password": "SigmaPass!2026"})
        self.assertRedirects(resp, reverse("home"))
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("login"))

    def test_profile_viewing_still_works(self):
        User.objects.create_user(username="erin", password="SigmaPass!2026")
        resp = self.client.get(reverse("profile", kwargs={"username": "erin"}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "@erin")

    def test_profile_editing_still_works(self):
        User.objects.create_user(username="frank", password="SigmaPass!2026")
        self.client.login(username="frank", password="SigmaPass!2026")
        resp = self.client.post(reverse("edit_profile"), {"bio": "Still works"}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Still works")


class LikeTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Likeable post")

    def test_authenticated_user_can_like_a_post(self):
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.post(reverse("toggle_like", kwargs={"pk": self.post.pk}), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Like.objects.filter(user=self.bob, post=self.post).exists())

    def test_authenticated_user_can_unlike_a_post(self):
        self.client.login(username="bob", password="pw12345!")
        # First click: like
        self.client.post(reverse("toggle_like", kwargs={"pk": self.post.pk}))
        self.assertTrue(Like.objects.filter(user=self.bob, post=self.post).exists())
        # Second click: unlike
        self.client.post(reverse("toggle_like", kwargs={"pk": self.post.pk}))
        self.assertFalse(Like.objects.filter(user=self.bob, post=self.post).exists())

    def test_like_count_is_correct(self):
        Like.objects.create(user=self.bob, post=self.post)
        carol = User.objects.create_user(username="carol", password="pw12345!")
        Like.objects.create(user=carol, post=self.post)
        post = Post.objects.with_engagement(self.alice).get(pk=self.post.pk)
        self.assertEqual(post.like_count, 2)

    def test_duplicate_like_prevented_at_db_level(self):
        Like.objects.create(user=self.bob, post=self.post)
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Like.objects.create(user=self.bob, post=self.post)
        # Still only one Like row exists.
        self.assertEqual(Like.objects.filter(user=self.bob, post=self.post).count(), 1)

    def test_toggle_like_view_never_creates_duplicate(self):
        self.client.login(username="bob", password="pw12345!")
        url = reverse("toggle_like", kwargs={"pk": self.post.pk})
        self.client.post(url)  # like
        self.client.post(url)  # unlike
        self.client.post(url)  # like again
        self.assertEqual(Like.objects.filter(user=self.bob, post=self.post).count(), 1)

    def test_correct_user_associated_with_like(self):
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("toggle_like", kwargs={"pk": self.post.pk}))
        like = Like.objects.get(post=self.post)
        self.assertEqual(like.user, self.bob)

    def test_anonymous_user_cannot_like(self):
        resp = self.client.post(reverse("toggle_like", kwargs={"pk": self.post.pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)
        self.assertFalse(Like.objects.filter(post=self.post).exists())

    def test_cannot_spoof_another_user_as_liker(self):
        """The like is always credited to request.user regardless of any submitted data."""
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("toggle_like", kwargs={"pk": self.post.pk}), {"user": self.alice.pk})
        like = Like.objects.get(post=self.post)
        self.assertEqual(like.user, self.bob)
        self.assertNotEqual(like.user, self.alice)

    def test_likes_list_shows_likers(self):
        Like.objects.create(user=self.bob, post=self.post)
        resp = self.client.get(reverse("post_likes", kwargs={"pk": self.post.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "@bob")


class CommentTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Commentable post")

    def test_authenticated_user_can_comment(self):
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.post(
            reverse("add_comment", kwargs={"pk": self.post.pk}),
            {"content": "Nice post!"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Comment.objects.filter(post=self.post, content="Nice post!").exists())

    def test_comment_associated_with_correct_post(self):
        other_post = Post.objects.create(author=self.alice, content="Another post")
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("add_comment", kwargs={"pk": self.post.pk}), {"content": "On the right post"})
        comment = Comment.objects.get(content="On the right post")
        self.assertEqual(comment.post, self.post)
        self.assertNotEqual(comment.post, other_post)

    def test_comment_associated_with_logged_in_user(self):
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("add_comment", kwargs={"pk": self.post.pk}), {"content": "Hi"})
        comment = Comment.objects.get(post=self.post)
        self.assertEqual(comment.author, self.bob)

    def test_cannot_spoof_comment_author(self):
        self.client.login(username="bob", password="pw12345!")
        self.client.post(
            reverse("add_comment", kwargs={"pk": self.post.pk}),
            {"content": "Spoof attempt", "author": self.alice.pk},
        )
        comment = Comment.objects.get(content="Spoof attempt")
        self.assertEqual(comment.author, self.bob)

    def test_empty_comment_rejected(self):
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.post(reverse("add_comment", kwargs={"pk": self.post.pk}), {"content": ""})
        self.assertEqual(resp.status_code, 200)  # re-rendered with errors
        self.assertFalse(Comment.objects.filter(post=self.post).exists())

    def test_whitespace_only_comment_rejected(self):
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.post(reverse("add_comment", kwargs={"pk": self.post.pk}), {"content": "    "})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Comment.objects.filter(post=self.post).exists())

    def test_anonymous_user_cannot_comment(self):
        resp = self.client.post(reverse("add_comment", kwargs={"pk": self.post.pk}), {"content": "Sneaky"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)
        self.assertFalse(Comment.objects.filter(post=self.post).exists())

    def test_comments_appear_on_correct_post_detail_page(self):
        Comment.objects.create(post=self.post, author=self.bob, content="Visible comment")
        resp = self.client.get(reverse("post_detail", kwargs={"pk": self.post.pk}))
        self.assertContains(resp, "Visible comment")

    def test_comment_count_is_correct(self):
        Comment.objects.create(post=self.post, author=self.bob, content="One")
        Comment.objects.create(post=self.post, author=self.bob, content="Two")
        post = Post.objects.with_engagement(self.alice).get(pk=self.post.pk)
        self.assertEqual(post.comment_count, 2)

    def test_comments_ordered_oldest_first(self):
        first = Comment.objects.create(post=self.post, author=self.bob, content="First")
        second = Comment.objects.create(post=self.post, author=self.bob, content="Second")
        comments = list(self.post.comments.all())
        self.assertEqual(comments[0], first)
        self.assertEqual(comments[1], second)


class CommentDeleteTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Post with a comment")
        self.comment = Comment.objects.create(post=self.post, author=self.bob, content="Bob's comment")

    def test_author_can_delete_own_comment(self):
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.post(reverse("delete_comment", kwargs={"pk": self.comment.pk}), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_other_user_cannot_delete_comment(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(reverse("delete_comment", kwargs={"pk": self.comment.pk}))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_anonymous_user_cannot_delete_comment(self):
        resp = self.client.post(reverse("delete_comment", kwargs={"pk": self.comment.pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)
        self.assertTrue(Comment.objects.filter(pk=self.comment.pk).exists())


class Phase5RegressionTests(TestCase):
    """Confirm Phases 1-4 still work after Phase 5 changes."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="SigmaPass!2026")

    def test_registration_still_works(self):
        resp = self.client.post(
            reverse("register"),
            {"username": "carol", "password1": "SigmaPass!2026", "password2": "SigmaPass!2026"},
        )
        self.assertRedirects(resp, reverse("login"))

    def test_login_and_logout_still_work(self):
        resp = self.client.post(reverse("login"), {"username": "alice", "password": "SigmaPass!2026"})
        self.assertRedirects(resp, reverse("home"))
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("login"))

    def test_profile_viewing_and_editing_still_work(self):
        resp = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertEqual(resp.status_code, 200)
        self.client.login(username="alice", password="SigmaPass!2026")
        resp = self.client.post(reverse("edit_profile"), {"bio": "Still works"}, follow=True)
        self.assertContains(resp, "Still works")

    def test_post_creation_and_feed_still_work(self):
        self.client.login(username="alice", password="SigmaPass!2026")
        self.client.post(reverse("create_post"), {"content": "Regression post"})
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Regression post")

    def test_post_deletion_still_works(self):
        post = Post.objects.create(author=self.alice, content="Delete me")
        self.client.login(username="alice", password="SigmaPass!2026")
        resp = self.client.post(reverse("delete_post", kwargs={"pk": post.pk}), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())


class PostSecurityTests(TestCase):
    """Phase 9 security audit: XSS escaping, upload validation, CSRF."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")

    def test_post_content_html_is_escaped(self):
        self.client.login(username="alice", password="pw12345!")
        payload = "<script>alert('XSS')</script>"
        self.client.post(reverse("create_post"), {"content": payload})
        resp = self.client.get(reverse("home"))
        self.assertNotContains(resp, "<script>alert('XSS')</script>")
        self.assertContains(resp, "&lt;script&gt;")

    def test_comment_content_html_is_escaped(self):
        post = Post.objects.create(author=self.alice, content="Comment on me")
        self.client.login(username="bob", password="pw12345!")
        payload = "<img src=x onerror=alert(1)>"
        self.client.post(reverse("add_comment", kwargs={"pk": post.pk}), {"content": payload})
        resp = self.client.get(reverse("post_detail", kwargs={"pk": post.pk}))
        self.assertNotContains(resp, "<img src=x onerror=alert(1)>")

    def test_non_image_file_disguised_as_image_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake_image = SimpleUploadedFile(
            "malicious.jpg", b"#!/bin/sh\necho not an image", content_type="image/jpeg"
        )
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(
            reverse("create_post"), {"content": "test", "image": fake_image}
        )
        self.assertEqual(resp.status_code, 200)  # re-rendered with errors
        self.assertFalse(Post.objects.filter(content="test").exists())

    def test_oversized_post_image_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from image_validators import MAX_UPLOAD_SIZE_BYTES

        buf = io.BytesIO()
        Image.new("RGB", (10, 10), color="blue").save(buf, format="PNG")
        oversized = SimpleUploadedFile(
            "big.png", buf.getvalue() + b"0" * (MAX_UPLOAD_SIZE_BYTES + 1), content_type="image/png"
        )
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(
            reverse("create_post"), {"content": "test oversize", "image": oversized}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Post.objects.filter(content="test oversize").exists())

    def test_create_post_requires_csrf(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.login(username="alice", password="pw12345!")
        resp = csrf_client.post(reverse("create_post"), {"content": "no csrf"})
        self.assertEqual(resp.status_code, 403)

    def test_toggle_like_requires_csrf(self):
        post = Post.objects.create(author=self.alice, content="likeable")
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.login(username="bob", password="pw12345!")
        resp = csrf_client.post(reverse("toggle_like", kwargs={"pk": post.pk}))
        self.assertEqual(resp.status_code, 403)

    def test_delete_post_requires_csrf(self):
        post = Post.objects.create(author=self.alice, content="delete me")
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.login(username="alice", password="pw12345!")
        resp = csrf_client.post(reverse("delete_post", kwargs={"pk": post.pk}))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())
