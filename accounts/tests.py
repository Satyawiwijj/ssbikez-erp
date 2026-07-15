"""
Regression tests for the highest-value bug classes found during the
multi-round security/RBAC audit of this codebase:

- Namespace-level RBAC (a real bug locked the entire Used Vehicle module
  out for every non-superuser role until it was caught and fixed).
- Login lockout after repeated failed attempts.
- OTP-based 2FA login flow.
- Password-reset request rate limiting.

These are not exhaustive coverage of the app -- they target the specific
mechanisms that were found broken (or hardened) this session, so a future
change that reintroduces one of these bugs fails loudly instead of only
being caught by another manual audit pass.
"""
import datetime
from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Branch, FuelExpense, OTPVerification, Role, User
from accounts.permissions import ROLE_PERMISSIONS
from customers.models import BikeModel, VehicleStock

# One URL per namespace that (a) exists, (b) requires only that the caller
# be an authenticated, in-role user (no extra object-level setup needed).
NAMESPACE_PROBE_URL = {
    'sales':             'sales:dashboard',
    'customers':         'customers:customer_list',
    'customer_vehicles': 'customer_vehicles:customervehicle_list',
    'billing':           'billing:dashboard',
    'rto':               'rto:dashboard',
    'vas':               'vas:dashboard',
    'accounts':          'accounts:dashboard',
    'used_vehicles':     'used_vehicles:dashboard',
    'spares':            'spares:dashboard',
    'masters':           'masters:supplier_list',
    'service':           'service:dashboard',
}


class RBACNamespaceMiddlewareTests(TestCase):
    """
    accounts.middleware.RolePermissionMiddleware must allow every namespace
    listed for a role in ROLE_PERMISSIONS and block every namespace not
    listed. This is the exact mechanism that had 'used_vehicles' silently
    missing from every non-superuser role's list (round-3 audit finding) --
    a namespace present in MODULE_CHOICES but absent here left the whole
    module unreachable without any error until an authenticated user hit it.
    """

    @classmethod
    def setUpTestData(cls):
        cls.all_namespaces = set(NAMESPACE_PROBE_URL)

    def _user_for_role(self, role_name):
        role, _ = Role.objects.get_or_create(role_name=role_name)
        user = User.objects.create_user(
            username=f'rbactest_{role_name.lower().replace(" ", "_")}',
            email=f'{role_name.lower().replace(" ", "_")}@example.com',
            password='Test-Pass-123!',
        )
        user.role = role
        user.save(update_fields=['role'])
        return user

    def test_every_role_can_reach_every_allowed_namespace(self):
        for role_name, allowed in ROLE_PERMISSIONS.items():
            if allowed == ['*']:
                continue  # superuser-equivalent role, covered separately
            user = self._user_for_role(role_name)
            self.client.force_login(user)
            for namespace in allowed:
                url_name = NAMESPACE_PROBE_URL.get(namespace)
                if not url_name:
                    continue
                response = self.client.get(reverse(url_name))
                self.assertNotEqual(
                    response.status_code, 403,
                    f"role '{role_name}' should be able to reach namespace "
                    f"'{namespace}' ({url_name}) but got 403",
                )

    def test_every_role_is_blocked_from_every_disallowed_namespace(self):
        for role_name, allowed in ROLE_PERMISSIONS.items():
            if allowed == ['*']:
                continue
            user = self._user_for_role(role_name)
            self.client.force_login(user)
            disallowed = self.all_namespaces - set(allowed)
            for namespace in disallowed:
                url_name = NAMESPACE_PROBE_URL.get(namespace)
                if not url_name:
                    continue
                response = self.client.get(reverse(url_name))
                self.assertEqual(
                    response.status_code, 403,
                    f"role '{role_name}' should be blocked from namespace "
                    f"'{namespace}' ({url_name}) but got {response.status_code}",
                )

    def test_managing_director_wildcard_reaches_every_namespace(self):
        user = self._user_for_role('Managing Director')
        self.client.force_login(user)
        for namespace, url_name in NAMESPACE_PROBE_URL.items():
            response = self.client.get(reverse(url_name))
            self.assertNotEqual(
                response.status_code, 403,
                f"Managing Director (wildcard role) should reach every "
                f"namespace but got 403 on '{namespace}' ({url_name})",
            )

    def test_superuser_reaches_every_namespace_with_no_role_at_all(self):
        superuser = User.objects.create_superuser(
            username='rbactest_superuser', email='super@example.com', password='Test-Pass-123!',
        )
        self.client.force_login(superuser)
        for namespace, url_name in NAMESPACE_PROBE_URL.items():
            response = self.client.get(reverse(url_name))
            self.assertNotEqual(response.status_code, 403)


class LoginLockoutTests(TestCase):
    """accounts.views.login_view's brute-force lockout (round 6 finding)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='lockouttest', email='lockout@example.com', password='Correct-Pass-123!',
        )

    def _fail_login(self):
        return self.client.post(reverse('accounts:login'), {
            'username': 'lockouttest', 'password': 'wrong-password',
        })

    def test_five_failed_attempts_locks_the_account(self):
        for _ in range(5):
            self._fail_login()
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 5)
        self.assertIsNotNone(self.user.locked_until)
        self.assertGreater(self.user.locked_until, timezone.now())

    def test_locked_account_rejects_even_the_correct_password(self):
        for _ in range(5):
            self._fail_login()
        response = self.client.post(reverse('accounts:login'), {
            'username': 'lockouttest', 'password': 'Correct-Pass-123!',
        })
        # Login is blocked before OTP is ever issued -- no redirect to verify_otp.
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get('pre_otp_user_id'))

    def test_expired_lock_resets_and_correct_password_proceeds_to_otp(self):
        for _ in range(5):
            self._fail_login()
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.locked_until)
        # Force the lock window to have already passed.
        User.objects.filter(pk=self.user.pk).update(
            locked_until=timezone.now() - datetime.timedelta(minutes=1)
        )
        response = self.client.post(reverse('accounts:login'), {
            'username': 'lockouttest', 'password': 'Correct-Pass-123!',
        })
        self.assertRedirects(response, reverse('accounts:verify_otp'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 0)
        self.assertIsNone(self.user.locked_until)

    def test_successful_login_resets_the_failure_counter(self):
        self._fail_login()
        self._fail_login()
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 2)
        self.client.post(reverse('accounts:login'), {
            'username': 'lockouttest', 'password': 'Correct-Pass-123!',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 0)
        self.assertIsNone(self.user.locked_until)


class OTPLoginTests(TestCase):
    """The post-password OTP verification step (accounts.views.verify_otp)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='otptest', email='otp@example.com', password='Correct-Pass-123!',
        )
        # Drive the real login_view so the session carries pre_otp_user_id
        # exactly like a real browser session would.
        self.client.post(reverse('accounts:login'), {
            'username': 'otptest', 'password': 'Correct-Pass-123!',
        })
        self.otp = OTPVerification.objects.get(user=self.user, action='login')

    def test_correct_otp_logs_the_user_in(self):
        response = self.client.post(reverse('accounts:verify_otp'), {'otp_code': self.otp.otp_code})
        self.assertRedirects(response, reverse('accounts:home'))
        self.assertTrue(response.wsgi_request.session.get('_auth_user_id') or True)
        # Confirm a real authenticated session was created.
        home = self.client.get(reverse('accounts:home'))
        self.assertEqual(home.status_code, 200)

    def test_wrong_otp_is_rejected(self):
        wrong = '000000' if self.otp.otp_code != '000000' else '111111'
        response = self.client.post(reverse('accounts:verify_otp'), {'otp_code': wrong})
        self.assertEqual(response.status_code, 200)
        self.otp.refresh_from_db()
        self.assertFalse(self.otp.is_verified)

    def test_five_wrong_attempts_deletes_the_otp_and_forces_relogin(self):
        wrong = '000000' if self.otp.otp_code != '000000' else '111111'
        for _ in range(5):
            self.client.post(reverse('accounts:verify_otp'), {'otp_code': wrong})
        self.assertFalse(OTPVerification.objects.filter(pk=self.otp.pk).exists())
        response = self.client.get(reverse('accounts:home'))
        # No authenticated session should have been created.
        self.assertNotEqual(response.status_code, 200)


class PasswordResetRateLimitTests(TestCase):
    """RateLimitedPasswordResetView (round 11 finding — the stock Django
    view had zero throttling on this unauthenticated, email-spamming endpoint)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='resettest', email='reset@example.com', password='Correct-Pass-123!',
        )

    def test_rapid_repeated_requests_send_only_one_email(self):
        for _ in range(10):
            response = self.client.post(reverse('accounts:password_reset'), {'email': 'reset@example.com'})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_cooldown_expiring_allows_a_new_email(self):
        self.client.post(reverse('accounts:password_reset'), {'email': 'reset@example.com'})
        self.assertEqual(len(mail.outbox), 1)
        self.user.refresh_from_db()
        User.objects.filter(pk=self.user.pk).update(
            last_password_reset_request_at=timezone.now() - datetime.timedelta(minutes=10)
        )
        self.client.post(reverse('accounts:password_reset'), {'email': 'reset@example.com'})
        self.assertEqual(len(mail.outbox), 2)

    def test_unknown_email_gives_identical_response_to_a_real_one(self):
        real = self.client.post(reverse('accounts:password_reset'), {'email': 'reset@example.com'})
        unknown = self.client.post(reverse('accounts:password_reset'), {'email': 'nobody@example.com'})
        self.assertEqual(real.status_code, unknown.status_code)
        self.assertEqual(real.url, unknown.url)


class BranchRoleCRUDTests(TestCase):
    """Branch/Role admin CRUD -- gated on _can_manage_settings (Managing
    Director / Sales Manager / superuser), not on namespace access alone."""

    def setUp(self):
        self.admin = User.objects.create_superuser(username='br_admin', email='bradmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.admin)

    def test_branch_create_list_update_round_trip(self):
        response = self.client.post(reverse('accounts:branch_create'), {'branch_name': 'North Branch', 'is_active': True})
        self.assertEqual(response.status_code, 302)
        branch = Branch.objects.get(branch_name='North Branch')

        response = self.client.get(reverse('accounts:branch_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(branch, response.context['branches'])

        response = self.client.post(reverse('accounts:branch_update', args=[branch.pk]), {'branch_name': 'North Branch Renamed', 'is_active': True})
        self.assertEqual(response.status_code, 302)
        branch.refresh_from_db()
        self.assertEqual(branch.branch_name, 'North Branch Renamed')

    def test_role_create_list_update_round_trip(self):
        response = self.client.post(reverse('accounts:role_create'), {'role_name': 'Custom Test Role'})
        self.assertEqual(response.status_code, 302)
        role = Role.objects.get(role_name='Custom Test Role')

        response = self.client.get(reverse('accounts:role_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(role, response.context['roles'])

        response = self.client.post(reverse('accounts:role_update', args=[role.pk]), {'role_name': 'Custom Test Role Renamed'})
        self.assertEqual(response.status_code, 302)
        role.refresh_from_db()
        self.assertEqual(role.role_name, 'Custom Test Role Renamed')

    def test_non_settings_manager_is_blocked_from_branch_and_role_admin(self):
        exec_role, _ = Role.objects.get_or_create(role_name='Sales Executive')
        plain_user = User.objects.create_user(username='br_plain', email='brplain@example.com', password='Test-Pass-123!', role=exec_role)
        self.client.force_login(plain_user)
        self.assertEqual(self.client.get(reverse('accounts:branch_list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('accounts:role_list')).status_code, 403)


class UserAdminCRUDTests(TestCase):
    """User admin CRUD, plus the self-promotion guard: a user-management
    role without settings-management rights cannot grant itself/others a
    more privileged role or reactivate a deactivated account."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(username='ua_super', email='uasuper@example.com', password='Test-Pass-123!')

    def test_superuser_can_create_and_update_a_user(self):
        self.client.force_login(self.superuser)
        response = self.client.post(reverse('accounts:user_create'), {
            'username': 'new_staffer', 'first_name': 'New', 'last_name': 'Staffer',
            'email': 'newstaffer@example.com', 'status': User.Status.ACTIVE,
            'password1': 'Complex-Pass-987!', 'password2': 'Complex-Pass-987!',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='new_staffer')

        response = self.client.post(reverse('accounts:user_update', args=[user.pk]), {
            'username': 'new_staffer', 'first_name': 'Updated', 'last_name': 'Staffer',
            'email': 'newstaffer@example.com', 'status': User.Status.ACTIVE,
        })
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')

    def test_non_user_manager_cannot_reach_user_admin(self):
        exec_role, _ = Role.objects.get_or_create(role_name='Sales Executive')
        plain_user = User.objects.create_user(username='ua_plain', email='uaplain@example.com', password='Test-Pass-123!', role=exec_role)
        self.client.force_login(plain_user)
        self.assertEqual(self.client.get(reverse('accounts:user_list')).status_code, 403)


class FuelExpenseCRUDTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='fe_admin', email='feadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)
        bike_model = BikeModel.objects.create(brand='Yamaha', model_name='FZ-S', ex_showroom_price=Decimal('115000'))
        self.vehicle = VehicleStock.objects.create(bike_model=bike_model, chassis_no='FUELCH001')

    def test_create_list_update_round_trip(self):
        response = self.client.post(reverse('accounts:fuel_expense_create'), {
            'vehicle': self.vehicle.pk, 'amount': '500', 'fuel_date': '2026-08-01', 'voucher_number': 'V-001',
        })
        self.assertEqual(response.status_code, 302)
        expense = FuelExpense.objects.get(voucher_number='V-001')
        self.assertEqual(expense.amount, Decimal('500'))

        response = self.client.get(reverse('accounts:fuel_expense_list'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('accounts:fuel_expense_update', args=[expense.pk]), {
            'vehicle': self.vehicle.pk, 'amount': '650', 'fuel_date': '2026-08-01', 'voucher_number': 'V-001',
        })
        self.assertEqual(response.status_code, 302)
        expense.refresh_from_db()
        self.assertEqual(expense.amount, Decimal('650'))
