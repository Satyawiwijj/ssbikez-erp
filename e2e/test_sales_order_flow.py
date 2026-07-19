"""
Real-browser smoke test for the Sales Order docstatus lifecycle
(Draft -> Submitted -> Cancelled), the core document every other Sales flow
in this app hangs off of.
"""
from accounts.models import Role
from sales.models import VehicleSalesOrder

from e2e.base import PlaywrightTestCase
from e2e.fixtures import make_customer


class SalesOrderLifecycleTest(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        role = Role.objects.create(role_name='E2E Sales')
        self.user = self.make_user('e2e_sales_user', role=role, is_superuser=True)
        self.login_as(self.user)
        self.order = VehicleSalesOrder.objects.create(customer=make_customer(), total_amount=0)

    def test_submit_then_cancel(self):
        page = self.page
        self.goto(f'/sales/orders/{self.order.pk}/')

        assert page.get_by_text('Draft').first.is_visible()

        page.get_by_role('button', name='Submit').click()
        page.wait_for_load_state('networkidle')
        assert page.get_by_text('Submitted').first.is_visible()
        assert page.get_by_text('Draft', exact=True).count() == 0

        page.once('dialog', lambda dialog: dialog.accept())
        page.get_by_role('button', name='Cancel').click()
        page.wait_for_load_state('networkidle')
        assert page.get_by_text('Cancelled').first.is_visible()

    def test_list_page_shows_order(self):
        self.goto('/sales/orders/')
        assert self.page.get_by_text(f'ORD-{self.order.pk}').is_visible()
