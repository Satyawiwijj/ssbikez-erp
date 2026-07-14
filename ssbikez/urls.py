from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='accounts:login', permanent=False)),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('customers/', include('customers.urls', namespace='customers')),
    path('customer-vehicles/', include('customer_vehicles.urls', namespace='customer_vehicles')),
    path('sales/', include('sales.urls', namespace='sales')),
    path('billing/', include('billing.urls', namespace='billing')),
    path('rto/', include('rto.urls', namespace='rto')),
    path('service/', include('service.urls', namespace='service')),
    path('spares/', include('spares.urls', namespace='spares')),
    path('vas/', include('vas.urls', namespace='vas')),
    path('masters/', include('masters.urls', namespace='masters')),
    path('used-vehicles/', include('used_vehicles.urls', namespace='used_vehicles')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

