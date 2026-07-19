"""
Drives the actual multi-formset Sales Order create form through a real
browser -- the harder, higher-value E2E pattern (vs. seeding via the ORM and
only exercising the detail-page buttons, as in test_sales_order_flow.py).
This is exactly the class of form where a template/formset wiring mistake
(wrong prefix, missing management_form, a field silently dropped) would
otherwise only surface as "the save button doesn't work" in production.
"""
from accounts.models import Role

from e2e.base import PlaywrightTestCase
from e2e.fixtures import make_customer


class SalesOrderCreateFormTest(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        role = Role.objects.create(role_name='E2E Sales Create')
        self.user = self.make_user('e2e_sales_create_user', role=role, is_superuser=True)
        self.login_as(self.user)
        self.customer = make_customer(full_name='E2E Formset Customer')

    def test_create_order_with_item_row(self):
        page = self.page
        self.goto('/sales/orders/create/')

        page.get_by_label('Customer', exact=True).select_option(str(self.customer.pk))

        # Required header fields with no browser-default prefill. Real
        # business minimums enforced in VehicleSalesOrderForm.clean():
        # booking_amount >= 1,000, total_amount >= 50,000.
        page.locator('[name="booking_amount"]').fill('1000')
        page.locator('[name="discount_amount"]').fill('0')
        page.locator('[name="total_amount"]').fill('50000')

        # The Items formset has exactly one blank row (extra=1) -- target it
        # by its Django-generated form field name, not get_by_label: "Item
        # name" is ambiguous on this page (the Additional Fittings formset
        # has its own item_name field with the same accessible label).
        page.locator('[name="items-0-item_name"]').fill('E2E Test Helmet')
        page.locator('[name="items-0-quantity"]').fill('2')
        page.locator('[name="items-0-rate"]').fill('500')

        page.get_by_role('button', name='Save Order').click()
        page.wait_for_load_state('networkidle')

        # A successful save redirects to the detail page; a validation
        # failure re-renders the create form instead -- fail loudly on the
        # wrong outcome rather than asserting page content that could
        # coincidentally match either page.
        if '/create/' in page.url:
            errs = page.locator('.form-error, .alert-danger').all_text_contents()
            raise AssertionError(f'form did not save; errors on page: {errs}')
        assert '/sales/orders/' in page.url

        assert page.get_by_text('E2E Test Helmet').first.is_visible()
        assert page.get_by_text('E2E Formset Customer').first.is_visible()

    def test_missing_required_field_reshows_form_with_error(self):
        page = self.page
        self.goto('/sales/orders/create/')
        # Submit with every field left blank -- booking_amount/total_amount/
        # sales_status/payment_status are all form-required with no
        # browser-default prefill, so this must re-render with an inline
        # error, not silently redirect or 500.
        page.get_by_role('button', name='Save Order').click()
        page.wait_for_load_state('networkidle')

        assert '/create/' in page.url
        assert page.get_by_text('Please correct the errors below.').is_visible()
