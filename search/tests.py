from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from connections.models import Follow
from posts.models import Post


class SearchPageTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.client.login(username="alice", password="pw12345!")

    def test_search_page_loads(self):
        resp = self.client.get(reverse("search"))
        self.assertEqual(resp.status_code, 200)

    def test_search_url_with_query_works(self):
        resp = self.client.get(reverse("search") + "?q=alice")
        self.assertEqual(resp.status_code, 200)

    def test_empty_search_shows_friendly_prompt(self):
        resp = self.client.get(reverse("search"))
        self.assertContains(resp, "Find people and posts")

    def test_whitespace_only_search_treated_as_empty(self):
        resp = self.client.get(reverse("search") + "?q=   ")
        self.assertContains(resp, "Find people and posts")

    def test_excessively_long_query_does_not_crash(self):
        long_query = "a" * 5000
        resp = self.client.get(reverse("search"), {"q": long_query})
        self.assertEqual(resp.status_code, 200)

    def test_malicious_query_does_not_error(self):
        for payload in ["'; DROP TABLE auth_user; --", "<script>alert(1)</script>", "%00%00", "??**"]:
            resp = self.client.get(reverse("search"), {"q": payload})
            self.assertEqual(resp.status_code, 200)

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        resp = self.client.get(reverse("search") + "?q=alice")
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)


class UserSearchTests(TestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(username="viewer", password="pw12345!")
        self.sarah = User.objects.create_user(
            username="sarah", password="pw12345!", first_name="Sarah", last_name="Kamara"
        )
        self.client.login(username="viewer", password="pw12345!")

    def test_username_search_finds_user(self):
        resp = self.client.get(reverse("search"), {"q": "sarah"})
        self.assertContains(resp, "@sarah")

    def test_first_name_search_finds_user(self):
        resp = self.client.get(reverse("search"), {"q": "Sarah"})
        self.assertContains(resp, "@sarah")

    def test_last_name_search_finds_user(self):
        resp = self.client.get(reverse("search"), {"q": "Kamara"})
        self.assertContains(resp, "@sarah")

    def test_case_insensitive_search(self):
        resp = self.client.get(reverse("search"), {"q": "SARAH"})
        self.assertContains(resp, "@sarah")

    def test_partial_search(self):
        resp = self.client.get(reverse("search"), {"q": "sar"})
        self.assertContains(resp, "@sarah")

    def test_no_matching_users(self):
        resp = self.client.get(reverse("search"), {"q": "zzz_no_such_user"})
        self.assertContains(resp, "No people found")


class PostSearchTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author", password="pw12345!")
        self.viewer = User.objects.create_user(username="viewer", password="pw12345!")
        self.post = Post.objects.create(author=self.author, content="Anyone watching the football match?")
        self.client.login(username="viewer", password="pw12345!")

    def test_matching_post_content_found(self):
        resp = self.client.get(reverse("search"), {"q": "football"})
        self.assertContains(resp, "football match")

    def test_case_insensitive_post_search(self):
        resp = self.client.get(reverse("search"), {"q": "FOOTBALL"})
        self.assertContains(resp, "football match")

    def test_partial_content_search(self):
        resp = self.client.get(reverse("search"), {"q": "footb"})
        self.assertContains(resp, "football match")

    def test_no_matching_posts(self):
        resp = self.client.get(reverse("search"), {"q": "zzz_no_such_content"})
        self.assertContains(resp, "No posts found")

    def test_post_result_links_to_post_detail(self):
        resp = self.client.get(reverse("search"), {"q": "football"})
        self.assertContains(resp, reverse("post_detail", kwargs={"pk": self.post.pk}))


class SearchPaginationTests(TestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(username="viewer", password="pw12345!")
        self.client.login(username="viewer", password="pw12345!")
        for i in range(15):
            User.objects.create_user(username=f"testuser{i}", password="pw12345!")
            Post.objects.create(author=self.viewer, content=f"test post number {i}")

    def test_user_results_are_paginated(self):
        resp = self.client.get(reverse("search"), {"q": "testuser"})
        self.assertEqual(resp.context["user_page_obj"].paginator.num_pages, 2)
        self.assertEqual(len(resp.context["user_page_obj"]), 10)

    def test_post_results_are_paginated(self):
        resp = self.client.get(reverse("search"), {"q": "test post"})
        self.assertEqual(resp.context["post_page_obj"].paginator.num_pages, 2)
        self.assertEqual(len(resp.context["post_page_obj"]), 10)

    def test_query_preserved_on_user_pagination_page(self):
        resp = self.client.get(reverse("search"), {"q": "testuser", "upage": 2})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["query"], "testuser")
        self.assertEqual(len(resp.context["user_page_obj"]), 5)

    def test_query_preserved_on_post_pagination_page(self):
        resp = self.client.get(reverse("search"), {"q": "test post", "page": 2})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["query"], "test post")
        self.assertEqual(len(resp.context["post_page_obj"]), 5)


class ExploreTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.client.login(username="alice", password="pw12345!")

    def test_explore_page_loads(self):
        resp = self.client.get(reverse("explore"))
        self.assertEqual(resp.status_code, 200)

    def test_recent_posts_appear(self):
        Post.objects.create(author=self.alice, content="Explore me")
        resp = self.client.get(reverse("explore"))
        self.assertContains(resp, "Explore me")

    def test_posts_appear_newest_first(self):
        older = Post.objects.create(author=self.alice, content="Older explore post")
        newer = Post.objects.create(author=self.alice, content="Newer explore post")
        resp = self.client.get(reverse("explore"))
        posts = list(resp.context["page_obj"])
        self.assertEqual(posts[0], newer)
        self.assertEqual(posts[1], older)

    def test_explore_pagination_works(self):
        for i in range(15):
            Post.objects.create(author=self.alice, content=f"Explore post {i}")
        resp = self.client.get(reverse("explore"))
        self.assertEqual(resp.context["page_obj"].paginator.num_pages, 2)

    def test_empty_explore_shows_friendly_message(self):
        resp = self.client.get(reverse("explore"))
        self.assertContains(resp, "Nothing to explore yet")

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        resp = self.client.get(reverse("explore"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)


class SuggestedUsersTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.carol = User.objects.create_user(username="carol", password="pw12345!")
        self.client.login(username="alice", password="pw12345!")

    def test_current_user_excluded_from_suggestions(self):
        resp = self.client.get(reverse("explore"))
        suggested_usernames = [u.username for u in resp.context["suggested_users"]]
        self.assertNotIn("alice", suggested_usernames)

    def test_already_followed_users_excluded(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        resp = self.client.get(reverse("explore"))
        suggested_usernames = [u.username for u in resp.context["suggested_users"]]
        self.assertNotIn("bob", suggested_usernames)
        self.assertIn("carol", suggested_usernames)

    def test_follow_state_correct_in_suggestions(self):
        resp = self.client.get(reverse("explore"))
        # Suggestions are, by construction, never-followed -- so every
        # suggested user should show a Follow button, not Following.
        follow_url = reverse("follow_user", kwargs={"username": "bob"})
        self.assertContains(resp, f'action="{follow_url}"')

    def test_following_everyone_shows_friendly_message(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        Follow.objects.create(follower=self.alice, following=self.carol)
        resp = self.client.get(reverse("explore"))
        self.assertContains(resp, "You're following everyone!")


class SearchFollowIntegrationTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.sarah = User.objects.create_user(username="sarah", password="pw12345!")
        self.client.login(username="alice", password="pw12345!")

    def test_user_result_links_to_correct_profile(self):
        resp = self.client.get(reverse("search"), {"q": "sarah"})
        self.assertContains(resp, reverse("profile", kwargs={"username": "sarah"}))

    def test_own_result_shows_you_not_follow_button(self):
        resp = self.client.get(reverse("search"), {"q": "alice"})
        self.assertContains(resp, ">You<")

    def test_not_following_shows_follow_button(self):
        resp = self.client.get(reverse("search"), {"q": "sarah"})
        follow_url = reverse("follow_user", kwargs={"username": "sarah"})
        self.assertContains(resp, f'action="{follow_url}"')

    def test_already_following_shows_following_button(self):
        Follow.objects.create(follower=self.alice, following=self.sarah)
        resp = self.client.get(reverse("search"), {"q": "sarah"})
        unfollow_url = reverse("unfollow_user", kwargs={"username": "sarah"})
        self.assertContains(resp, f'action="{unfollow_url}"')

    def test_follow_from_search_result_works(self):
        from notifications.models import Notification

        follow_url = reverse("follow_user", kwargs={"username": "sarah"})
        resp = self.client.get(reverse("search"), {"q": "sarah"})
        self.assertContains(resp, f'action="{follow_url}"')

        self.client.post(follow_url)
        self.assertTrue(Follow.objects.filter(follower=self.alice, following=self.sarah).exists())
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.sarah, actor=self.alice, notification_type="FOLLOW"
            ).exists()
        )


class SearchSecurityTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice", password="pw12345!", email="alice@example.com"
        )
        self.client.login(username="alice", password="pw12345!")

    def test_email_not_exposed_in_search_results(self):
        resp = self.client.get(reverse("search"), {"q": "alice"})
        self.assertNotContains(resp, "alice@example.com")

    def test_password_hash_not_exposed(self):
        resp = self.client.get(reverse("search"), {"q": "alice"})
        self.assertNotContains(resp, self.alice.password)


class SearchRegressionTests(TestCase):
    """Confirm Phases 1-7 still work after Phase 8 changes."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="SigmaPass!2026")

    def test_registration_login_logout_still_work(self):
        resp = self.client.post(
            reverse("register"),
            {"username": "dave", "password1": "SigmaPass!2026", "password2": "SigmaPass!2026"},
        )
        self.assertRedirects(resp, reverse("login"))
        resp = self.client.post(reverse("login"), {"username": "alice", "password": "SigmaPass!2026"})
        self.assertRedirects(resp, reverse("home"))
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("login"))

    def test_profile_still_works(self):
        resp = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertEqual(resp.status_code, 200)

    def test_posts_and_feed_still_work(self):
        self.client.login(username="alice", password="SigmaPass!2026")
        self.client.post(reverse("create_post"), {"content": "Regression post"})
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Regression post")

    def test_likes_comments_still_work(self):
        bob = User.objects.create_user(username="bob", password="pw12345!")
        post = Post.objects.create(author=self.alice, content="Engage with me")
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("toggle_like", kwargs={"pk": post.pk}))
        self.client.post(reverse("add_comment", kwargs={"pk": post.pk}), {"content": "Nice"})
        self.assertEqual(post.likes.count(), 1)
        self.assertEqual(post.comments.count(), 1)

    def test_notifications_still_work(self):
        from notifications.models import Notification

        bob = User.objects.create_user(username="bob", password="pw12345!")
        self.client.login(username="alice", password="SigmaPass!2026")
        self.client.post(reverse("create_post"), {"content": "New post"})
        self.assertTrue(Notification.objects.filter(recipient=bob, notification_type="NEW_POST").exists())

    def test_followers_following_still_work(self):
        bob = User.objects.create_user(username="bob", password="pw12345!")
        self.client.login(username="alice", password="SigmaPass!2026")
        self.client.post(reverse("follow_user", kwargs={"username": "bob"}))
        self.assertTrue(Follow.objects.filter(follower=self.alice, following=bob).exists())
        resp = self.client.get(reverse("following"))
        self.assertContains(resp, "@bob")
