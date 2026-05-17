from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('customers/', include('customers.urls', namespace='customers')),
    path('customer-vehicles/', include('customer_vehicles.urls', namespace='customer_vehicles')),
    path('sales/', include('sales.urls', namespace='sales')),
    path('', RedirectView.as_view(pattern_name='accounts:login', permanent=False)),
]
