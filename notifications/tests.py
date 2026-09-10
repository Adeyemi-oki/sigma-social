from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from posts.models import Comment, Like, Post
from .models import Notification


class NotificationModelTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="A post")

    def test_notification_can_be_created(self):
        n = Notification.objects.create(
            recipient=self.alice,
            actor=self.bob,
            notification_type=Notification.NotificationType.LIKE,
            post=self.post,
        )
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(n.recipient, self.alice)
        self.assertEqual(n.actor, self.bob)

    def test_defaults_to_unread(self):
        n = Notification.objects.create(
            recipient=self.alice,
            actor=self.bob,
            notification_type=Notification.NotificationType.LIKE,
            post=self.post,
        )
        self.assertFalse(n.is_read)

    def test_relationships(self):
        comment = Comment.objects.create(post=self.post, author=self.bob, content="hi")
        n = Notification.objects.create(
            recipient=self.alice,
            actor=self.bob,
            notification_type=Notification.NotificationType.COMMENT,
            post=self.post,
            comment=comment,
        )
        self.assertEqual(n.post, self.post)
        self.assertEqual(n.comment, comment)
        self.assertIn(n, self.alice.notifications.all())
        self.assertIn(n, self.bob.notifications_sent.all())


class NewPostNotificationTests(TestCase):
    def setUp(self):
        self.john = User.objects.create_user(username="john", password="pw12345!")
        self.sarah = User.objects.create_user(username="sarah", password="pw12345!")
        self.amina = User.objects.create_user(username="amina", password="pw12345!")
        self.mohamed = User.objects.create_user(username="mohamed", password="pw12345!")

    def test_creating_a_post_notifies_other_users_not_the_author(self):
        self.client.login(username="john", password="pw12345!")
        self.client.post(reverse("create_post"), {"content": "Hello everyone"})

        post = Post.objects.get(author=self.john)

        self.assertEqual(Notification.objects.filter(recipient=self.john).count(), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.sarah).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.amina).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.mohamed).count(), 1)

        sarah_notification = Notification.objects.get(recipient=self.sarah)
        self.assertEqual(sarah_notification.actor, self.john)
        self.assertEqual(sarah_notification.post, post)
        self.assertEqual(sarah_notification.notification_type, Notification.NotificationType.NEW_POST)


class LikeNotificationTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Likeable")

    def test_liking_another_users_post_notifies_the_owner(self):
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("toggle_like", kwargs={"pk": self.post.pk}))

        self.assertEqual(Notification.objects.filter(recipient=self.alice).count(), 1)
        n = Notification.objects.get(recipient=self.alice)
        self.assertEqual(n.actor, self.bob)
        self.assertEqual(n.notification_type, Notification.NotificationType.LIKE)
        self.assertEqual(n.post, self.post)

    def test_liker_does_not_get_notified(self):
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("toggle_like", kwargs={"pk": self.post.pk}))
        self.assertEqual(Notification.objects.filter(recipient=self.bob).count(), 0)

    def test_liking_own_post_creates_no_notification(self):
        self.client.login(username="alice", password="pw12345!")
        self.client.post(reverse("toggle_like", kwargs={"pk": self.post.pk}))
        self.assertEqual(Notification.objects.count(), 0)

    def test_repeated_like_unlike_does_not_create_duplicate_notifications(self):
        self.client.login(username="bob", password="pw12345!")
        url = reverse("toggle_like", kwargs={"pk": self.post.pk})
        self.client.post(url)  # like -> 1 notification
        self.client.post(url)  # unlike -> no new notification
        self.client.post(url)  # like again -> 1 more notification
        self.assertEqual(Notification.objects.filter(recipient=self.alice, notification_type="LIKE").count(), 2)


class CommentNotificationTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Commentable")

    def test_commenting_on_another_users_post_notifies_the_owner(self):
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("add_comment", kwargs={"pk": self.post.pk}), {"content": "Nice!"})

        comment = Comment.objects.get(post=self.post)
        n = Notification.objects.get(recipient=self.alice)
        self.assertEqual(n.actor, self.bob)
        self.assertEqual(n.notification_type, Notification.NotificationType.COMMENT)
        self.assertEqual(n.comment, comment)

    def test_commenting_on_own_post_creates_no_notification(self):
        self.client.login(username="alice", password="pw12345!")
        self.client.post(reverse("add_comment", kwargs={"pk": self.post.pk}), {"content": "My own comment"})
        self.assertEqual(Notification.objects.count(), 0)


class NotificationAccessTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Post")
        self.notification = Notification.objects.create(
            recipient=self.alice,
            actor=self.bob,
            notification_type=Notification.NotificationType.LIKE,
            post=self.post,
        )

    def test_authenticated_user_can_view_their_notifications(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("notifications"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "@bob")

    def test_anonymous_user_cannot_access_notification_page(self):
        resp = self.client.get(reverse("notifications"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)

    def test_user_cannot_see_another_users_notifications_in_list(self):
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.get(reverse("notifications"))
        self.assertNotContains(resp, "liked your post")


class MarkAsReadTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Post")
        self.notification = Notification.objects.create(
            recipient=self.alice,
            actor=self.bob,
            notification_type=Notification.NotificationType.LIKE,
            post=self.post,
        )

    def test_user_can_mark_own_notification_as_read(self):
        self.client.login(username="alice", password="pw12345!")
        self.client.post(reverse("mark_notification_read", kwargs={"pk": self.notification.pk}))
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_user_cannot_mark_another_users_notification_as_read(self):
        self.client.login(username="bob", password="pw12345!")
        resp = self.client.post(reverse("mark_notification_read", kwargs={"pk": self.notification.pk}))
        self.assertEqual(resp.status_code, 403)
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_anonymous_user_cannot_mark_as_read(self):
        resp = self.client.post(reverse("mark_notification_read", kwargs={"pk": self.notification.pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)


class MarkAllAsReadTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Post")
        for _ in range(3):
            Notification.objects.create(
                recipient=self.alice,
                actor=self.bob,
                notification_type=Notification.NotificationType.LIKE,
                post=self.post,
            )
        self.bobs_notification = Notification.objects.create(
            recipient=self.bob,
            actor=self.alice,
            notification_type=Notification.NotificationType.LIKE,
            post=self.post,
        )

    def test_mark_all_read_marks_all_of_current_users_notifications(self):
        self.client.login(username="alice", password="pw12345!")
        self.client.post(reverse("mark_all_notifications_read"))
        self.assertEqual(Notification.objects.filter(recipient=self.alice, is_read=False).count(), 0)

    def test_mark_all_read_does_not_touch_other_users_notifications(self):
        self.client.login(username="alice", password="pw12345!")
        self.client.post(reverse("mark_all_notifications_read"))
        self.bobs_notification.refresh_from_db()
        self.assertFalse(self.bobs_notification.is_read)


class UnreadCountTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Post")

    def test_unread_count_is_correct(self):
        for _ in range(2):
            Notification.objects.create(
                recipient=self.alice, actor=self.bob,
                notification_type=Notification.NotificationType.LIKE, post=self.post,
            )
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.context["unread_notifications_count"], 2)

    def test_read_notifications_excluded_from_count(self):
        Notification.objects.create(
            recipient=self.alice, actor=self.bob,
            notification_type=Notification.NotificationType.LIKE, post=self.post, is_read=True,
        )
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.context["unread_notifications_count"], 0)

    def test_other_users_notifications_excluded_from_count(self):
        Notification.objects.create(
            recipient=self.bob, actor=self.alice,
            notification_type=Notification.NotificationType.LIKE, post=self.post,
        )
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.context["unread_notifications_count"], 0)

    def test_anonymous_unread_count_is_zero_and_does_not_error(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["unread_notifications_count"], 0)


class Phase6RegressionTests(TestCase):
    """Confirm Phases 1-5 still work after Phase 6 changes."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="SigmaPass!2026")

    def test_registration_login_logout_still_work(self):
        resp = self.client.post(
            reverse("register"),
            {"username": "carol", "password1": "SigmaPass!2026", "password2": "SigmaPass!2026"},
        )
        self.assertRedirects(resp, reverse("login"))

        resp = self.client.post(reverse("login"), {"username": "alice", "password": "SigmaPass!2026"})
        self.assertRedirects(resp, reverse("home"))
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("login"))

    def test_profile_still_works(self):
        resp = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertEqual(resp.status_code, 200)
        self.client.login(username="alice", password="SigmaPass!2026")
        resp = self.client.post(reverse("edit_profile"), {"bio": "Still works"}, follow=True)
        self.assertContains(resp, "Still works")

    def test_posts_feed_still_work(self):
        self.client.login(username="alice", password="SigmaPass!2026")
        self.client.post(reverse("create_post"), {"content": "Regression post"})
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Regression post")

    def test_likes_and_comments_still_work(self):
        bob = User.objects.create_user(username="bob", password="pw12345!")
        post = Post.objects.create(author=self.alice, content="Engage with me")

        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("toggle_like", kwargs={"pk": post.pk}))
        self.assertTrue(Like.objects.filter(user=bob, post=post).exists())

        self.client.post(reverse("add_comment", kwargs={"pk": post.pk}), {"content": "Nice one"})
        self.assertTrue(Comment.objects.filter(post=post, author=bob).exists())

    def test_comment_deletion_still_works(self):
        self.client.login(username="alice", password="SigmaPass!2026")
        post = Post.objects.create(author=self.alice, content="Post")
        comment = Comment.objects.create(post=post, author=self.alice, content="delete me")
        resp = self.client.post(reverse("delete_comment", kwargs={"pk": comment.pk}), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())


class NotificationSecurityTests(TestCase):
    """Phase 9 security audit: CSRF on state-changing notification actions."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.post = Post.objects.create(author=self.alice, content="Post")
        self.notification = Notification.objects.create(
            recipient=self.alice,
            actor=self.bob,
            notification_type=Notification.NotificationType.LIKE,
            post=self.post,
        )

    def test_mark_read_requires_csrf(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.login(username="alice", password="pw12345!")
        resp = csrf_client.post(reverse("mark_notification_read", kwargs={"pk": self.notification.pk}))
        self.assertEqual(resp.status_code, 403)

    def test_mark_all_read_requires_csrf(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.login(username="alice", password="pw12345!")
        resp = csrf_client.post(reverse("mark_all_notifications_read"))
        self.assertEqual(resp.status_code, 403)
