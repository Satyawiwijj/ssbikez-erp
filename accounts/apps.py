from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        # Admin branding — applied once Django is fully loaded
        from django.contrib import admin
        admin.site.site_header  = 'SSBikez ERP Administration'
        admin.site.site_title   = 'SSBikez ERP'
        admin.site.index_title  = 'Welcome to SSBikez ERP Admin'
