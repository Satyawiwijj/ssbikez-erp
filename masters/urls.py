from django.urls import path
from . import views

app_name = 'masters'

urlpatterns = [
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),

    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.supplier_update, name='supplier_update'),

    # Warehouses
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/create/', views.warehouse_create, name='warehouse_create'),
    path('warehouses/<int:pk>/edit/', views.warehouse_update, name='warehouse_update'),

    # Racks
    path('racks/', views.rack_list, name='rack_list'),
    path('racks/create/', views.rack_create, name='rack_create'),
    path('racks/<int:pk>/edit/', views.rack_update, name='rack_update'),

    # Bins
    path('bins/', views.bin_list, name='bin_list'),
    path('bins/create/', views.bin_create, name='bin_create'),
    path('bins/<int:pk>/edit/', views.bin_update, name='bin_update'),

    # Phase 8a — Order Form Settings & Order Form Series
    path('order-form-settings/', views.order_form_settings, name='order_form_settings'),
    path('order-form-settings/generate/', views.order_form_settings_generate, name='order_form_settings_generate'),
    path('order-form-series/', views.order_form_series_list, name='order_form_series_list'),
    path('order-form-series/<int:pk>/', views.order_form_series_detail, name='order_form_series_detail'),
    path('order-form-series/<int:pk>/cancel/', views.order_form_series_cancel, name='order_form_series_cancel'),

    # Phase 8b — Model and Price
    path('model-and-price/', views.model_and_price_list, name='model_and_price_list'),
    path('model-and-price/create/', views.model_and_price_create, name='model_and_price_create'),
    path('model-and-price/<int:pk>/', views.model_and_price_detail, name='model_and_price_detail'),
    path('model-and-price/<int:pk>/edit/', views.model_and_price_update, name='model_and_price_update'),

    # Phase 8b — Customer Price
    path('customer-price/', views.customer_price_list, name='customer_price_list'),
    path('customer-price/create/', views.customer_price_create, name='customer_price_create'),
    path('customer-price/<int:pk>/', views.customer_price_detail, name='customer_price_detail'),
    path('customer-price/<int:pk>/edit/', views.customer_price_update, name='customer_price_update'),

    # Phase 8b — Dealer Price List
    path('dealer-price-list/', views.dealer_price_list_list, name='dealer_price_list_list'),
    path('dealer-price-list/create/', views.dealer_price_list_create, name='dealer_price_list_create'),
    path('dealer-price-list/<int:pk>/', views.dealer_price_list_detail, name='dealer_price_list_detail'),
    path('dealer-price-list/<int:pk>/edit/', views.dealer_price_list_update, name='dealer_price_list_update'),

    # Phase 8c — Vehicle Fitting Spares
    path('vehicle-fitting-spares/', views.vehicle_fitting_spares_list, name='vehicle_fitting_spares_list'),
    path('vehicle-fitting-spares/create/', views.vehicle_fitting_spares_create, name='vehicle_fitting_spares_create'),
    path('vehicle-fitting-spares/<int:pk>/', views.vehicle_fitting_spares_detail, name='vehicle_fitting_spares_detail'),
    path('vehicle-fitting-spares/<int:pk>/edit/', views.vehicle_fitting_spares_update, name='vehicle_fitting_spares_update'),
]
