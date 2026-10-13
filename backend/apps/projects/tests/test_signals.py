from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.projects.signals import _ensure_admin_user


class DefaultAdminInitializationTests(TestCase):
    def test_creates_default_admin_once(self):
        User = get_user_model()
        User.objects.filter(username='admin').delete()

        _ensure_admin_user()
        admin = User.objects.get(username='admin')

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password('aistory'))

        admin.set_password('custom-password')
        admin.save(update_fields=['password'])
        _ensure_admin_user()
        admin.refresh_from_db()
        self.assertTrue(admin.check_password('custom-password'))
