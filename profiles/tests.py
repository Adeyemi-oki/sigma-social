import io

from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase
from PIL import Image


def make_test_image():
    """Build a small in-memory PNG for upload tests, avoiding a fixture file."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
    buf.seek(0)
    buf.name = "test.png"
    return buf


class ProfileCreationTests(TestCase):
    def test_profile_created_automatically_on_user_creation(self):
        user = User.objects.create_user(username="alice", password="pw12345!")
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.user, user)

    def test_profile_not_duplicated_on_subsequent_saves(self):
        from profiles.models import Profile

        user = User.objects.create_user(username="bob", password="pw12345!")
        profile_id = user.profile.id
        user.email = "bob@example.com"
        user.save()  # triggers post_save again
        user.refresh_from_db()
        self.assertEqual(user.profile.id, profile_id)
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)


class ProfileViewTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")

    def test_can_view_own_profile(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "@alice")
        self.assertContains(resp, "Edit Profile")

    def test_can_view_another_users_profile(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("profile", kwargs={"username": "bob"}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "@bob")
        # Alice viewing Bob's profile should not see an edit button
        self.assertNotContains(resp, "Edit Profile")

    def test_anonymous_user_can_view_a_profile(self):
        resp = self.client.get(reverse("profile", kwargs={"username": "bob"}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "@bob")

    def test_unknown_username_returns_404(self):
        resp = self.client.get(reverse("profile", kwargs={"username": "doesnotexist"}))
        self.assertEqual(resp.status_code, 404)


class ProfileEditTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")

    def test_unauthenticated_user_cannot_access_edit_page(self):
        resp = self.client.get(reverse("edit_profile"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)

    def test_authenticated_user_can_edit_own_bio(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(
            reverse("edit_profile"),
            {"bio": "Hello, this is my bio."},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.profile.bio, "Hello, this is my bio.")

    def test_edit_redirects_to_own_profile(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(reverse("edit_profile"), {"bio": "Hi"})
        self.assertRedirects(resp, reverse("profile", kwargs={"username": "alice"}))

    def test_profile_picture_upload(self):
        self.client.login(username="alice", password="pw12345!")
        image = make_test_image()
        resp = self.client.post(
            reverse("edit_profile"),
            {"bio": "Has a picture", "profile_picture": image},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.alice.refresh_from_db()
        self.assertTrue(bool(self.alice.profile.profile_picture))

    def test_edit_page_only_ever_targets_own_profile(self):
        """
        There is no username parameter on the edit URL, so there is no
        way to target another user's profile through it -- but we also
        confirm here that submitting a form while logged in as bob only
        ever changes bob's profile, never alice's.
        """
        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("edit_profile"), {"bio": "Bob's own bio"})

        self.alice.refresh_from_db()
        self.bob.refresh_from_db()
        self.assertEqual(self.bob.profile.bio, "Bob's own bio")
        self.assertNotEqual(self.alice.profile.bio, "Bob's own bio")


class ProfileUrlTests(TestCase):
    def test_profile_url_resolves(self):
        url = reverse("profile", kwargs={"username": "someone"})
        self.assertEqual(url, "/profile/someone/")

    def test_edit_profile_url_resolves(self):
        url = reverse("edit_profile")
        self.assertEqual(url, "/profile/edit/")


class ExistingAuthStillWorksTests(TestCase):
    """Regression checks: Phase 2 registration/login/logout must still work."""

    def test_registration_still_works(self):
        resp = self.client.post(
            reverse("register"),
            {"username": "carol", "password1": "SigmaPass!2026", "password2": "SigmaPass!2026"},
        )
        self.assertRedirects(resp, reverse("login"))
        self.assertTrue(User.objects.filter(username="carol").exists())
        # And registering a user still creates their profile (Phase 3 hook).
        self.assertTrue(hasattr(User.objects.get(username="carol"), "profile"))

    def test_login_and_logout_still_work(self):
        User.objects.create_user(username="dave", password="SigmaPass!2026")
        resp = self.client.post(
            reverse("login"),
            {"username": "dave", "password": "SigmaPass!2026"},
        )
        self.assertRedirects(resp, reverse("home"))
        self.assertTrue("_auth_user_id" in self.client.session)

        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("login"))
        self.assertFalse("_auth_user_id" in self.client.session)


class ProfileSecurityTests(TestCase):
    """Phase 9 security audit: profile ownership, XSS, upload validation."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")

    def test_bio_html_is_escaped_not_executed(self):
        self.client.login(username="alice", password="pw12345!")
        payload = "<script>alert('XSS')</script>"
        self.client.post(reverse("edit_profile"), {"bio": payload})
        resp = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertNotContains(resp, "<script>alert('XSS')</script>")
        self.assertContains(resp, "&lt;script&gt;")

    def test_editing_never_touches_another_users_profile(self):
        """
        There is no username parameter on /profile/edit/ -- it always
        operates on request.user.profile. Confirm two different users
        editing in sequence only ever change their own row.
        """
        self.client.login(username="alice", password="pw12345!")
        self.client.post(reverse("edit_profile"), {"bio": "Alice's bio"})
        self.client.logout()

        self.client.login(username="bob", password="pw12345!")
        self.client.post(reverse("edit_profile"), {"bio": "Bob's bio"})

        self.alice.refresh_from_db()
        self.bob.refresh_from_db()
        self.assertEqual(self.alice.profile.bio, "Alice's bio")
        self.assertEqual(self.bob.profile.bio, "Bob's bio")

    def test_valid_image_upload_accepted(self):
        self.client.login(username="alice", password="pw12345!")
        image = make_test_image()
        resp = self.client.post(
            reverse("edit_profile"), {"bio": "hi", "profile_picture": image}, follow=True
        )
        self.assertEqual(resp.status_code, 200)
        self.alice.refresh_from_db()
        self.assertTrue(bool(self.alice.profile.profile_picture))

    def test_non_image_file_disguised_as_image_rejected(self):
        """
        Django's ImageField uses Pillow to verify the file is actually
        a decodable image -- a text file renamed to .png/.jpg must
        fail validation, not be accepted and stored.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake_image = SimpleUploadedFile(
            "malicious.png", b"not actually a png file", content_type="image/png"
        )
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(reverse("edit_profile"), {"bio": "hi", "profile_picture": fake_image})
        self.assertEqual(resp.status_code, 200)  # re-rendered with errors, not saved
        self.alice.refresh_from_db()
        self.assertFalse(bool(self.alice.profile.profile_picture))

    def test_oversized_image_rejected(self):
        import io as io_module

        from django.core.files.uploadedfile import SimpleUploadedFile
        from image_validators import MAX_UPLOAD_SIZE_BYTES

        buf = io_module.BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
        content = buf.getvalue()
        # Pad past the size limit while keeping a valid PNG structure
        # irrelevant -- the size check runs before Pillow decodes it.
        oversized = SimpleUploadedFile(
            "big.png", content + b"0" * (MAX_UPLOAD_SIZE_BYTES + 1), content_type="image/png"
        )
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(reverse("edit_profile"), {"bio": "hi", "profile_picture": oversized})
        self.assertEqual(resp.status_code, 200)
        self.alice.refresh_from_db()
        self.assertFalse(bool(self.alice.profile.profile_picture))

    def test_edit_profile_requires_csrf(self):
        self.client.login(username="alice", password="pw12345!")
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.login(username="alice", password="pw12345!")
        resp = csrf_client.post(reverse("edit_profile"), {"bio": "no csrf token"})
        self.assertEqual(resp.status_code, 403)
