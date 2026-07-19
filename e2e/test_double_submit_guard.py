"""
Verifies base.html's global double-submit guard covers <button> elements
that rely on the HTML default (submit, when no type="..." is set) rather
than declaring type="submit" explicitly -- e.g. the RC Hand Over detail
page's Submit button. Found via a ui-ux-pro-max audit: the guard's original
selector (`button[type="submit"]`) silently missed these.
"""
from used_vehicles.models import UsedVehicleRCHandOver

from accounts.models import Role
from e2e.base import PlaywrightTestCase
from e2e.fixtures import make_used_vehicle_sale


class DoubleSubmitGuardTest(PlaywrightTestCase):
    def setUp(self):
        super().setUp()
        role = Role.objects.create(role_name='E2E Guard')
        self.user = self.make_user('e2e_guard_user', role=role, is_superuser=True)
        self.login_as(self.user)
        sale = make_used_vehicle_sale()
        self.handover = UsedVehicleRCHandOver.objects.create(sale=sale, rc_number='RC-GUARD-1')

    def test_submit_button_with_no_explicit_type_gets_disabled(self):
        page = self.page
        self.goto(f'/used-vehicles/rc-handover/{self.handover.pk}/')

        submit_locator = page.get_by_role('button', name='Submit')
        # Confirm the fixture matches the real, unmodified template shape
        # (no type="submit" attribute) -- if this ever changes, the test
        # should be revisited, not silently pass for the wrong reason.
        assert submit_locator.get_attribute('type') is None

        # Freeze a reference to this exact DOM node. A live-requerying
        # Locator (get_by_role(name='Submit')) stops matching the instant
        # the guard renames the button to "Saving..." -- which is the
        # behavior under test, so re-resolving by that same name afterward
        # would always time out.
        submit_btn = submit_locator.element_handle()

        # base.html's guard runs synchronously inside the 'submit' event
        # handler, which the spec guarantees completes in full before the
        # browser begins the actual network navigation -- so checking the
        # button's state via one JS round-trip immediately after a native
        # click (not Locator.click(), which would itself wait on the
        # navigation this test doesn't want to sit through) observes the
        # guard's effect deterministically, not as a timing race.
        state = submit_btn.evaluate("""
            (el) => {
                el.click();
                return {disabled: el.disabled, text: el.textContent};
            }
        """)
        assert state['disabled'] is True
        assert 'Saving' in state['text']
