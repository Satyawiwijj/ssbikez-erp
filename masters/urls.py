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
]
