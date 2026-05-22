from django.urls import path
from . import views

app_name = 'spares'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Items
    path('items/', views.item_list, name='item_list'),
    path('items/create/', views.item_create, name='item_create'),
    path('items/<int:pk>/', views.item_detail, name='item_detail'),
    path('items/<int:pk>/edit/', views.item_update, name='item_update'),

    # Stock
    path('stock/', views.stock_report, name='stock_report'),

    # Supplier Quotes
    path('quotes/', views.quote_list, name='quote_list'),
    path('quotes/create/', views.quote_create, name='quote_create'),
    path('quotes/<int:pk>/', views.quote_detail, name='quote_detail'),
    path('quotes/<int:pk>/edit/', views.quote_update, name='quote_update'),

    # Purchase Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/create/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/edit/', views.order_update, name='order_update'),

    # Purchase Invoices
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),

    # Counter Sales
    path('counter-sales/', views.counter_sale_list, name='counter_sale_list'),
    path('counter-sales/create/', views.counter_sale_create, name='counter_sale_create'),
    path('counter-sales/<int:pk>/', views.counter_sale_detail, name='counter_sale_detail'),

    # Counter Returns
    path('counter-returns/', views.counter_return_list, name='counter_return_list'),
    path('counter-returns/create/', views.counter_return_create, name='counter_return_create'),
    path('counter-returns/<int:pk>/', views.counter_return_detail, name='counter_return_detail'),

    # Issue Alterations
    path('issue-alterations/', views.issue_alteration_list, name='issue_alteration_list'),
    path('issue-alterations/create/', views.issue_alteration_create, name='issue_alteration_create'),
    path('issue-alterations/<int:pk>/', views.issue_alteration_detail, name='issue_alteration_detail'),

    # Legacy backward-compat
    path('issue/create/', views.issue_alteration_create, name='issue_create'),

    # AJAX
    path('ajax/item-details/', views.ajax_item_details, name='ajax_item_details'),
    path('ajax/rack-bins/', views.ajax_rack_bins, name='ajax_rack_bins'),
]
