"""
Base class for real-browser E2E tests, driven with Playwright against a real
Django dev server (StaticLiveServerTestCase) -- the Django/Python equivalent
of a Next.js + Playwright setup: same "drive the actual app through a real
browser" intent, adapted to how this project already runs its 138 other
tests (`python manage.py test`, no pytest runner, no separate npm toolchain).

Run the whole E2E suite with:

    python manage.py test e2e

Run a single flow:

    python manage.py test e2e.test_sales_order_flow

First-time setup (one-off, not needed again after the first install):

    pip install playwright
    python -m playwright install chromium
"""
import os

# Playwright's sync API runs its own asyncio event loop in a background
# thread. Once it starts, Django's async-safety check (which just asks
# "is there a running event loop right now") misfires for ordinary
# synchronous ORM calls made from the test thread, even though they're not
# actually racing anything -- each thread has its own DB connection, and the
# ORM calls here never touch Playwright's loop. This is exactly the
# scenario Django's own DJANGO_ALLOW_ASYNC_UNSAFE escape hatch exists for
# (the same one used for Jupyter/IPython); must be set before Playwright
# (or Django) is imported/used anywhere in this process.
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.auth.hashers import make_password
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from playwright.sync_api import sync_playwright

from accounts.models import User

DEFAULT_PASSWORD = 'e2e-test-password-not-used'


class PlaywrightTestCase(StaticLiveServerTestCase):
    """
    Extend this for a real-browser flow test. Gives you `self.page` (a fresh
    Playwright Page per test method) already pointed at a real, running copy
    of the app, plus `self.login_as(user)` to get past auth without touching
    the OTP flow (2FA is exercised by its own tests in accounts/tests.py --
    forcing every E2E flow through a live email OTP would make these tests
    slow and flaky for no coverage benefit).
    """

    headless = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch(headless=cls.headless)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._playwright.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # Fresh context per test: isolates cookies/localStorage between
        # tests the same way a fresh incognito window would.
        self.context = self._browser.new_context(
            viewport={'width': 1440, 'height': 900}
        )
        self.page = self.context.new_page()

    def tearDown(self):
        self.context.close()
        super().tearDown()

    def goto(self, path):
        """Navigate to a path on the live test server, e.g. self.goto('/sales/orders/')."""
        self.page.goto(f'{self.live_server_url}{path}')

    def login_as(self, user):
        """
        Authenticate `self.page`'s browser context as `user` by injecting a
        real Django session cookie directly -- the same technique used
        throughout this session's own QA scripts, formalized here. This
        creates a genuine, valid session via Django's own session backend
        (not a mock), it just skips driving the login form + OTP screen for
        every single test.
        """
        session = SessionStore()
        session[SESSION_KEY] = str(user.pk)
        session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
        session[HASH_SESSION_KEY] = user.get_session_auth_hash()
        session.create()

        self.context.add_cookies([{
            'name': 'sessionid',
            'value': session.session_key,
            'url': self.live_server_url,
        }])

    @staticmethod
    def make_user(username, role=None, branch=None, is_superuser=False, **extra):
        """Create a real, saved User for a test -- password is irrelevant
        since tests authenticate via login_as(), never the login form."""
        user = User.objects.create(
            username=username,
            email=f'{username}@e2e.test',
            password=make_password(DEFAULT_PASSWORD),
            role=role,
            branch=branch,
            is_superuser=is_superuser,
            is_staff=is_superuser,
            is_active=True,
            **extra,
        )
        return user
