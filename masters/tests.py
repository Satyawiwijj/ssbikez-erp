"""
Regression tests for the Order Form Series batch-numbering generator
(Phase 8a) -- the numbering-series mechanism every downstream Sales Form/
RTO/Used-Vehicle document links to, and the ownership check on its own
cancel view (round-2 audit finding).
"""
from django.test import TestCase
from django.urls import reverse

from accounts.models import Branch, Role, User
from masters.models import OrderFormSettings, OrderFormSeries


class OrderFormSeriesGenerateTests(TestCase):

    def setUp(self):
        self.branch = Branch.objects.create(branch_name='Main Branch')
        self.user = User.objects.create_superuser(username='mfg_admin', email='mfgadmin@example.com', password='Test-Pass-123!')
        self.client.force_login(self.user)

    def _configure(self, **overrides):
        instance = OrderFormSettings.get_instance()
        instance.new_vehicle = True
        instance.branch = self.branch
        instance.prefix = 'ORD-'
        instance.digits = 5
        instance.count = 3
        for k, v in overrides.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def test_generate_creates_the_right_count_correctly_numbered_and_submitted(self):
        self._configure()
        self.client.post(reverse('masters:order_form_settings_generate'))
        series = list(OrderFormSeries.objects.order_by('order_form_no'))
        self.assertEqual(len(series), 3)
        self.assertEqual([s.order_form_no for s in series], ['ORD-00001', 'ORD-00002', 'ORD-00003'])
        for s in series:
            self.assertEqual(s.docstatus, OrderFormSeries.DocStatus.SUBMITTED)
            self.assertEqual(s.status, 'unused')

    def test_second_generate_call_continues_from_the_previous_highest_with_no_collisions(self):
        self._configure()
        self.client.post(reverse('masters:order_form_settings_generate'))
        self.client.post(reverse('masters:order_form_settings_generate'))
        numbers = list(OrderFormSeries.objects.order_by('order_form_no').values_list('order_form_no', flat=True))
        self.assertEqual(len(numbers), 6)
        self.assertEqual(len(numbers), len(set(numbers)), f"duplicate order_form_no values: {numbers}")
        self.assertEqual(numbers[-1], 'ORD-00006')

    def test_generate_blocked_without_branch_prefix_or_count(self):
        instance = OrderFormSettings.get_instance()
        instance.new_vehicle = True
        instance.save()  # branch/prefix/count left unset
        self.client.post(reverse('masters:order_form_settings_generate'))
        self.assertEqual(OrderFormSeries.objects.count(), 0)


class OrderFormSeriesOwnershipTests(TestCase):
    """order_form_series_cancel -- no submit view exists (rows are
    auto-submitted at generation time), but cancel is still ownership-gated
    via created_by, per the round-2 audit fix."""

    def setUp(self):
        role, _ = Role.objects.get_or_create(role_name='Spares')
        self.branch = Branch.objects.create(branch_name='Second Branch')
        self.owner = User.objects.create_user(username='ofs_owner', email='ofsowner@example.com', password='Test-Pass-123!', role=role)
        self.other = User.objects.create_user(username='ofs_other', email='ofsother@example.com', password='Test-Pass-123!', role=role)
        self.series = OrderFormSeries.objects.create(
            order_form_no='ORD-90001', branch=self.branch, status='unused',
            docstatus=OrderFormSeries.DocStatus.SUBMITTED, created_by=self.owner,
        )

    def test_non_owner_cannot_cancel(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('masters:order_form_series_cancel', args=[self.series.pk]))
        self.assertEqual(response.status_code, 403)

    def test_owner_can_cancel(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('masters:order_form_series_cancel', args=[self.series.pk]))
        self.assertEqual(response.status_code, 302)
        self.series.refresh_from_db()
        self.assertEqual(self.series.docstatus, OrderFormSeries.DocStatus.CANCELLED)
