from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from notifications.models import Notification
from .models import Follow
from .services import follower_count, following_count, is_following


class FollowCreationTests(TestCase):
    def setUp(self):
        self.john = User.objects.create_user(username="john", password="pw12345!")
        self.sarah = User.objects.create_user(username="sarah", password="pw12345!")

    def test_authenticated_user_can_follow_another_user(self):
        self.client.login(username="john", password="pw12345!")
        resp = self.client.post(reverse("follow_user", kwargs={"username": "sarah"}), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Follow.objects.filter(follower=self.john, following=self.sarah).exists())

    def test_follower_is_assigned_from_request_user(self):
        self.client.login(username="john", password="pw12345!")
        self.client.post(reverse("follow_user", kwargs={"username": "sarah"}))
        relationship = Follow.objects.get(following=self.sarah)
        self.assertEqual(relationship.follower, self.john)

    def test_cannot_spoof_follower_identity(self):
        """The follower is always request.user, regardless of any submitted data."""
        self.client.login(username="john", password="pw12345!")
        self.client.post(reverse("follow_user", kwargs={"username": "sarah"}), {"follower": 999})
        relationship = Follow.objects.get(following=self.sarah)
        self.assertEqual(relationship.follower, self.john)

    def test_anonymous_user_cannot_follow(self):
        resp = self.client.post(reverse("follow_user", kwargs={"username": "sarah"}))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)
        self.assertFalse(Follow.objects.exists())

    def test_follow_requires_post_not_get(self):
        self.client.login(username="john", password="pw12345!")
        resp = self.client.get(reverse("follow_user", kwargs={"username": "sarah"}))
        self.assertEqual(resp.status_code, 405)


class SelfFollowTests(TestCase):
    def setUp(self):
        self.john = User.objects.create_user(username="john", password="pw12345!")

    def test_user_cannot_follow_themselves_via_view(self):
        self.client.login(username="john", password="pw12345!")
        self.client.post(reverse("follow_user", kwargs={"username": "john"}))
        self.assertFalse(Follow.objects.exists())

    def test_self_follow_blocked_at_database_level(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Follow.objects.create(follower=self.john, following=self.john)


class DuplicateFollowTests(TestCase):
    def setUp(self):
        self.john = User.objects.create_user(username="john", password="pw12345!")
        self.sarah = User.objects.create_user(username="sarah", password="pw12345!")

    def test_duplicate_follow_via_view_does_not_create_second_row(self):
        self.client.login(username="john", password="pw12345!")
        url = reverse("follow_user", kwargs={"username": "sarah"})
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(Follow.objects.filter(follower=self.john, following=self.sarah).count(), 1)

    def test_duplicate_follow_blocked_at_database_level(self):
        Follow.objects.create(follower=self.john, following=self.sarah)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Follow.objects.create(follower=self.john, following=self.sarah)


class UnfollowTests(TestCase):
    def setUp(self):
        self.john = User.objects.create_user(username="john", password="pw12345!")
        self.sarah = User.objects.create_user(username="sarah", password="pw12345!")
        self.amina = User.objects.create_user(username="amina", password="pw12345!")
        Follow.objects.create(follower=self.john, following=self.sarah)

    def test_user_can_unfollow_someone_they_follow(self):
        self.client.login(username="john", password="pw12345!")
        self.client.post(reverse("unfollow_user", kwargs={"username": "sarah"}))
        self.assertFalse(Follow.objects.filter(follower=self.john, following=self.sarah).exists())

    def test_unfollow_only_removes_own_relationship(self):
        Follow.objects.create(follower=self.amina, following=self.sarah)
        self.client.login(username="john", password="pw12345!")
        self.client.post(reverse("unfollow_user", kwargs={"username": "sarah"}))
        self.assertTrue(Follow.objects.filter(follower=self.amina, following=self.sarah).exists())

    def test_unfollowing_someone_not_followed_is_safe(self):
        self.client.login(username="amina", password="pw12345!")
        resp = self.client.post(reverse("unfollow_user", kwargs={"username": "sarah"}), follow=True)
        self.assertEqual(resp.status_code, 200)  # no error, just a no-op

    def test_anonymous_user_cannot_unfollow(self):
        resp = self.client.post(reverse("unfollow_user", kwargs={"username": "sarah"}))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)


class ProfileIntegrationTests(TestCase):
    def setUp(self):
        self.john = User.objects.create_user(username="john", password="pw12345!")
        self.sarah = User.objects.create_user(username="sarah", password="pw12345!")
        self.amina = User.objects.create_user(username="amina", password="pw12345!")

    def test_follower_count_is_correct(self):
        Follow.objects.create(follower=self.sarah, following=self.john)
        Follow.objects.create(follower=self.amina, following=self.john)
        self.assertEqual(follower_count(self.john), 2)

    def test_following_count_is_correct(self):
        Follow.objects.create(follower=self.john, following=self.sarah)
        self.assertEqual(following_count(self.john), 1)

    def test_is_following_helper(self):
        Follow.objects.create(follower=self.john, following=self.sarah)
        self.assertTrue(is_following(self.john, self.sarah))
        self.assertFalse(is_following(self.sarah, self.john))

    def test_follow_button_shown_when_not_following(self):
        self.client.login(username="john", password="pw12345!")
        resp = self.client.get(reverse("profile", kwargs={"username": "sarah"}))
        self.assertContains(resp, ">Follow<")

    def test_following_button_shown_when_already_following(self):
        Follow.objects.create(follower=self.john, following=self.sarah)
        self.client.login(username="john", password="pw12345!")
        resp = self.client.get(reverse("profile", kwargs={"username": "sarah"}))
        self.assertContains(resp, ">Following<")

    def test_own_profile_does_not_show_follow_button(self):
        self.client.login(username="john", password="pw12345!")
        resp = self.client.get(reverse("profile", kwargs={"username": "john"}))
        follow_url = reverse("follow_user", kwargs={"username": "john"})
        unfollow_url = reverse("unfollow_user", kwargs={"username": "john"})
        self.assertNotContains(resp, f'action="{follow_url}"')
        self.assertNotContains(resp, f'action="{unfollow_url}"')

    def test_profile_shows_correct_counts(self):
        Follow.objects.create(follower=self.sarah, following=self.john)
        resp = self.client.get(reverse("profile", kwargs={"username": "john"}))
        self.assertEqual(resp.context["follower_count"], 1)
        self.assertEqual(resp.context["following_count"], 0)


class FollowersPageTests(TestCase):
    def setUp(self):
        self.john = User.objects.create_user(username="john", password="pw12345!")
        self.sarah = User.objects.create_user(username="sarah", password="pw12345!")
        Follow.objects.create(follower=self.sarah, following=self.john)

    def test_correct_followers_displayed(self):
        self.client.login(username="john", password="pw12345!")
        resp = self.client.get(reverse("followers"))
        self.assertContains(resp, "@sarah")

    def test_profile_link_present(self):
        self.client.login(username="john", password="pw12345!")
        resp = self.client.get(reverse("followers"))
        self.assertContains(resp, reverse("profile", kwargs={"username": "sarah"}))

    def test_authentication_required(self):
        resp = self.client.get(reverse("followers"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)


class FollowingPageTests(TestCase):
    def setUp(self):
        self.john = User.objects.create_user(username="john", password="pw12345!")
        self.sarah = User.objects.create_user(username="sarah", password="pw12345!")
        Follow.objects.create(follower=self.john, following=self.sarah)

    def test_correct_following_displayed(self):
        self.client.login(username="john", password="pw12345!")
        resp = self.client.get(reverse("following"))
        self.assertContains(resp, "@sarah")

    def test_profile_link_present(self):
        self.client.login(username="john", password="pw12345!")
        resp = self.client.get(reverse("following"))
        self.assertContains(resp, reverse("profile", kwargs={"username": "sarah"}))

    def test_authentication_required(self):
        resp = self.client.get(reverse("following"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)


class FollowNotificationTests(TestCase):
    def setUp(self):
        self.john = User.objects.create_user(username="john", password="pw12345!")
        self.sarah = User.objects.create_user(username="sarah", password="pw12345!")

    def test_follow_creates_notification_for_followed_user(self):
        self.client.login(username="sarah", password="pw12345!")
        self.client.post(reverse("follow_user", kwargs={"username": "john"}))
        n = Notification.objects.get(recipient=self.john)
        self.assertEqual(n.actor, self.sarah)
        self.assertEqual(n.notification_type, Notification.NotificationType.FOLLOW)

    def test_follower_does_not_receive_notification(self):
        self.client.login(username="sarah", password="pw12345!")
        self.client.post(reverse("follow_user", kwargs={"username": "john"}))
        self.assertEqual(Notification.objects.filter(recipient=self.sarah).count(), 0)

    def test_duplicate_follow_does_not_create_duplicate_notification(self):
        self.client.login(username="sarah", password="pw12345!")
        url = reverse("follow_user", kwargs={"username": "john"})
        self.client.post(url)
        self.client.post(url)  # already following -> no-op, no new notification
        self.assertEqual(Notification.objects.filter(recipient=self.john).count(), 1)

    def test_unfollow_then_refollow_creates_a_new_notification(self):
        self.client.login(username="sarah", password="pw12345!")
        self.client.post(reverse("follow_user", kwargs={"username": "john"}))
        self.client.post(reverse("unfollow_user", kwargs={"username": "john"}))
        self.client.post(reverse("follow_user", kwargs={"username": "john"}))
        self.assertEqual(Notification.objects.filter(recipient=self.john).count(), 2)


class FollowSecurityTests(TestCase):
    def setUp(self):
        self.john = User.objects.create_user(username="john", password="pw12345!")
        self.sarah = User.objects.create_user(username="sarah", password="pw12345!")
        self.amina = User.objects.create_user(username="amina", password="pw12345!")
        Follow.objects.create(follower=self.john, following=self.sarah)

    def test_user_cannot_remove_another_users_follow_relationship(self):
        """
        Amina logging in and hitting the unfollow URL for sarah only
        ever affects Amina's own (nonexistent) relationship with
        sarah -- it can never touch John's relationship, since the
        unfollow query is always scoped to follower=request.user.
        """
        self.client.login(username="amina", password="pw12345!")
        self.client.post(reverse("unfollow_user", kwargs={"username": "sarah"}))
        self.assertTrue(Follow.objects.filter(follower=self.john, following=self.sarah).exists())


class Phase7RegressionTests(TestCase):
    """Confirm Phases 1-6 still work after Phase 7 changes."""

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

    def test_posts_and_feed_still_work(self):
        self.client.login(username="alice", password="SigmaPass!2026")
        self.client.post(reverse("create_post"), {"content": "Regression post"})
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Regression post")

    def test_likes_and_comments_still_work(self):
        bob = User.objects.create_user(username="bob", password="pw12345!")
        from posts.models import Comment, Like, Post

        post = Post.objects.create(author=self.alice, content="Engage with me")
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("toggle_like", kwargs={"pk": post.pk}))
        self.assertTrue(Like.objects.filter(user=bob, post=post).exists())
        self.client.post(reverse("add_comment", kwargs={"pk": post.pk}), {"content": "Nice one"})
        self.assertTrue(Comment.objects.filter(post=post, author=bob).exists())

    def test_notifications_still_work(self):
        bob = User.objects.create_user(username="bob", password="pw12345!")
        self.client.login(username="alice", password="SigmaPass!2026")
        self.client.post(reverse("create_post"), {"content": "New post"})
        self.assertTrue(Notification.objects.filter(recipient=bob, notification_type="NEW_POST").exists())


class FollowCSRFTests(TestCase):
    """Phase 9 security audit: CSRF on follow/unfollow."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")

    def test_follow_requires_csrf(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.login(username="alice", password="pw12345!")
        resp = csrf_client.post(reverse("follow_user", kwargs={"username": "bob"}))
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Follow.objects.exists())

    def test_unfollow_requires_csrf(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.login(username="alice", password="pw12345!")
        resp = csrf_client.post(reverse("unfollow_user", kwargs={"username": "bob"}))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Follow.objects.filter(follower=self.alice, following=self.bob).exists())
