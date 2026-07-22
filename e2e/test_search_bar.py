from e2e.base import PlaywrightTestCase
from accounts.models import Role
from customers.models import Customer


class SearchBarClickTests(PlaywrightTestCase):

    def setUp(self):
        super().setUp()
        role = Role.objects.create(role_name='Managing Director')
        self.user = self.make_user('search_e2e_admin', role=role, is_superuser=True)
        Customer.objects.create(full_name='Findable Customer Search', phone='9998887770')

    def test_clicking_the_search_icon_submits_the_search(self):
        self.login_as(self.user)
        self.goto('/accounts/dashboard/')
        self.page.fill('#topbar-search-input', 'Findable Customer Search')
        # Click the magnifying-glass icon itself, not press Enter — this is
        # the exact interaction the client's report says doesn't work.
        self.page.click('.topbar form i.fa-search')
        self.page.wait_for_url('**/accounts/search/**')
        assert 'Findable Customer Search' in self.page.content()
