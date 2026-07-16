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
    path('stock-report/', views.stock_report),  # alias

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
    path('invoices/<int:pk>/edit/', views.invoice_update, name='invoice_update'),
    path('invoices/<int:pk>/submit/', views.invoice_submit, name='invoice_submit'),
    path('invoices/<int:pk>/cancel/', views.invoice_cancel, name='invoice_cancel'),
    path('invoices/<int:pk>/amend/', views.invoice_amend, name='invoice_amend'),

    # Counter Sales
    path('counter-sales/', views.counter_sale_list, name='counter_sale_list'),
    path('counter-sales/create/', views.counter_sale_create, name='counter_sale_create'),
    path('counter-sales/<int:pk>/', views.counter_sale_detail, name='counter_sale_detail'),
    path('counter-sales/<int:pk>/submit/', views.counter_sale_submit, name='counter_sale_submit'),
    path('counter-sales/<int:pk>/cancel/', views.counter_sale_cancel, name='counter_sale_cancel'),

    # Counter Returns
    path('counter-returns/', views.counter_return_list, name='counter_return_list'),
    path('counter-returns/create/', views.counter_return_create, name='counter_return_create'),
    path('counter-returns/<int:pk>/', views.counter_return_detail, name='counter_return_detail'),
    path('counter-returns/<int:pk>/cancel/', views.counter_return_cancel, name='counter_return_cancel'),

    # Issue Alterations
    path('issue-alterations/', views.issue_alteration_list, name='issue_alteration_list'),
    path('issue-alterations/create/', views.issue_alteration_create, name='issue_alteration_create'),
    path('issue-alterations/<int:pk>/', views.issue_alteration_detail, name='issue_alteration_detail'),
    path('issue-alterations/<int:pk>/cancel/', views.issue_alteration_cancel, name='issue_alteration_cancel'),

    # Legacy backward-compat
    path('issue/create/', views.issue_alteration_create, name='issue_create'),

    # GAP 13: Bulk Insert
    path('bulk-insert/', views.bulk_insert, name='bulk_insert'),

    # GAP 21: PO Used Qty Report
    path('reports/po-used-qty/', views.po_used_qty_report, name='po_used_qty_report'),

    # FEATURE 8 — Parts Consumption Report
    path('reports/parts-consumption/', views.parts_consumption_report, name='parts_consumption_report'),

    # Delete endpoints
    path('items/<int:pk>/delete/', views.item_delete, name='item_delete'),
    path('orders/<int:pk>/delete/', views.purchase_order_delete, name='order_delete'),

    # AJAX
    path('ajax/item-details/', views.ajax_item_details, name='ajax_item_details'),
    path('ajax/supplier-details/', views.ajax_supplier_details, name='ajax_supplier_details'),
    path('ajax/rack-bins/', views.ajax_rack_bins, name='ajax_rack_bins'),

    # Phase 7a — Stock Transfer
    path('stock-transfers/', views.stock_transfer_list, name='stock_transfer_list'),
    path('stock-transfers/create/', views.stock_transfer_create, name='stock_transfer_create'),
    path('stock-transfers/<int:pk>/', views.stock_transfer_detail, name='stock_transfer_detail'),
    path('stock-transfers/<int:pk>/submit/', views.stock_transfer_submit, name='stock_transfer_submit'),
    path('stock-transfers/<int:pk>/cancel/', views.stock_transfer_cancel, name='stock_transfer_cancel'),

    # Phase 7a — Stock Count Update (Spares Stock Reconciliation)
    path('stock-counts/', views.stock_count_list, name='stock_count_list'),
    path('stock-counts/create/', views.stock_count_create, name='stock_count_create'),
    path('stock-counts/<int:pk>/', views.stock_count_detail, name='stock_count_detail'),
    path('stock-counts/<int:pk>/submit/', views.stock_count_submit, name='stock_count_submit'),
    path('stock-counts/<int:pk>/cancel/', views.stock_count_cancel, name='stock_count_cancel'),

    # Phase 7a — Request Supplier Quote
    path('request-quotes/', views.request_supplier_quote_list, name='request_supplier_quote_list'),
    path('request-quotes/create/', views.request_supplier_quote_create, name='request_supplier_quote_create'),
    path('request-quotes/<int:pk>/', views.request_supplier_quote_detail, name='request_supplier_quote_detail'),
    path('request-quotes/<int:pk>/submit/', views.request_supplier_quote_submit, name='request_supplier_quote_submit'),
    path('request-quotes/<int:pk>/cancel/', views.request_supplier_quote_cancel, name='request_supplier_quote_cancel'),

    # Phase 7b — Spares Purchase Estimation Master
    path('estimations/', views.estimation_list, name='estimation_list'),
    path('estimations/create/', views.estimation_create, name='estimation_create'),
    path('estimations/<int:pk>/', views.estimation_detail, name='estimation_detail'),
    path('estimations/<int:pk>/submit/', views.estimation_submit, name='estimation_submit'),
    path('estimations/<int:pk>/cancel/', views.estimation_cancel, name='estimation_cancel'),

    # Phase 7c — Service Spares Issue Return
    path('service-spares-returns/', views.service_spares_issue_return_list, name='service_spares_issue_return_list'),
    path('service-spares-returns/create/', views.service_spares_issue_return_create, name='service_spares_issue_return_create'),
    path('service-spares-returns/<int:pk>/', views.service_spares_issue_return_detail, name='service_spares_issue_return_detail'),
    path('service-spares-returns/<int:pk>/submit/', views.service_spares_issue_return_submit, name='service_spares_issue_return_submit'),
    path('service-spares-returns/<int:pk>/cancel/', views.service_spares_issue_return_cancel, name='service_spares_issue_return_cancel'),

    # Phase 7d — Vehicle Spares Master
    path('vehicle-spares-master/', views.vehicle_spares_master_list, name='vehicle_spares_master_list'),
    path('vehicle-spares-master/create/', views.vehicle_spares_master_create, name='vehicle_spares_master_create'),

    # Phase 7d — Spares MRP Price Revision
    path('mrp-revisions/', views.mrp_revision_list, name='mrp_revision_list'),
    path('mrp-revisions/create/', views.mrp_revision_create, name='mrp_revision_create'),
    path('mrp-revisions/<int:pk>/', views.mrp_revision_detail, name='mrp_revision_detail'),
    path('mrp-revisions/<int:pk>/submit/', views.mrp_revision_submit, name='mrp_revision_submit'),
    path('mrp-revisions/<int:pk>/cancel/', views.mrp_revision_cancel, name='mrp_revision_cancel'),

    # Phase 7d — Spares Settings (Profit Percentage / Purchase Qty Days singles)
    path('settings/', views.spares_settings, name='spares_settings'),

    # Phase 7d — Service Spares Warranty
    path('service-spares-warranties/', views.service_spares_warranty_list, name='service_spares_warranty_list'),
    path('service-spares-warranties/create/', views.service_spares_warranty_create, name='service_spares_warranty_create'),
    path('service-spares-warranties/<int:pk>/', views.service_spares_warranty_detail, name='service_spares_warranty_detail'),
    path('service-spares-warranties/<int:pk>/submit/', views.service_spares_warranty_submit, name='service_spares_warranty_submit'),
    path('service-spares-warranties/<int:pk>/cancel/', views.service_spares_warranty_cancel, name='service_spares_warranty_cancel'),
]
