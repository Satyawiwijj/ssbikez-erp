"""
Real-browser coverage of the Used Vehicle RC Hand Over docstatus lifecycle
(Draft -> Submitted -> Cancelled) -- this is the exact feature this session
restructured onto DocStatusMixin, so this is the highest-value flow to lock
in with a real browser rather than a Client()-based test: it catches wiring
bugs (wrong URL, missing button, JS error, badge not updating) that a
request/response assertion can't see.
"""
from e2e.base import PlaywrightTestCase
from e2e.fixtures import make_used_vehicle_sale
from accounts.models import Role


class RCHandOverLifecycleTest(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        role = Role.objects.create(role_name='E2E Used Vehicles')
        self.user = self.make_user('e2e_uv_user', role=role, is_superuser=True)
        self.sale = make_used_vehicle_sale()
        self.login_as(self.user)

    def test_create_submit_cancel(self):
        page = self.page

        # --- Create ---
        self.goto('/used-vehicles/rc-handover/create/')
        page.get_by_label('Sale').select_option(str(self.sale.pk))
        page.get_by_label('Rc Number').fill('RC-E2E-0001')
        page.get_by_role('button', name='Save').click()

        page.wait_for_load_state('networkidle')
        assert '/used-vehicles/rc-handover/' in page.url
        assert page.get_by_text('Draft').first.is_visible()

        # --- Submit ---
        page.get_by_role('button', name='Submit').click()
        page.wait_for_load_state('networkidle')
        assert page.get_by_text('Submitted').first.is_visible()
        # Draft badge must be gone now, not just Submitted added alongside it.
        assert page.get_by_text('Draft', exact=True).count() == 0

        # --- Cancel ---
        page.once('dialog', lambda dialog: dialog.accept())
        page.get_by_role('button', name='Cancel').click()
        page.wait_for_load_state('networkidle')
        assert page.get_by_text('Cancelled').first.is_visible()

    def test_rc_number_persists_and_renders(self):
        self.goto('/used-vehicles/rc-handover/create/')
        self.page.get_by_label('Sale').select_option(str(self.sale.pk))
        self.page.get_by_label('Rc Number').fill('RC-PERSIST-9999')
        self.page.get_by_role('button', name='Save').click()
        self.page.wait_for_load_state('networkidle')

        assert self.page.get_by_text('RC-PERSIST-9999').is_visible()
