from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTest(TestCase):

    def test_create_user(self):
        u = User.objects.create_user(username="kavi", password="pass123", role="counsellor")
        self.assertEqual(u.username, "kavi")
        self.assertEqual(u.role, "counsellor")
        self.assertTrue(u.check_password("pass123"))

    def test_user_str(self):
        u = User.objects.create_user(username="admin1", password="pass123", role="admin", first_name="Super")
        self.assertIn("Super", str(u))

    def test_admin_role(self):
        u = User.objects.create_user(username="ad", password="pass123", role="admin")
        self.assertTrue(u.is_admin_role)
        self.assertTrue(u.is_super_admin)
        self.assertTrue(u.is_admin_user)
        self.assertFalse(u.is_counsellor_role)
        self.assertFalse(u.is_accountant_role)

    def test_counsellor_role(self):
        u = User.objects.create_user(username="co", password="pass123", role="counsellor")
        self.assertTrue(u.is_counsellor_role)
        self.assertFalse(u.is_admin_role)
        self.assertFalse(u.is_admin_user)
        self.assertFalse(u.is_accountant_role)

    def test_accountant_role(self):
        u = User.objects.create_user(username="acc", password="pass123", role="accountant")
        self.assertTrue(u.is_accountant_role)
        self.assertTrue(u.is_accounts)
        self.assertFalse(u.is_admin_role)
        self.assertFalse(u.is_counsellor_role)

    def test_superuser_is_admin(self):
        u = User.objects.create_superuser(username="root", password="pass123")
        self.assertTrue(u.is_super_admin)

    def test_user_ordering(self):
        u1 = User.objects.create_user(username="a", password="pass123")
        u2 = User.objects.create_user(username="b", password="pass123")
        users = list(User.objects.all())
        self.assertEqual(users[0], u2)
        self.assertEqual(users[1], u1)
