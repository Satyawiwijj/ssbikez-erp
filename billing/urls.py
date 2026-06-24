from django.urls import path

from . import pdf_views, views

app_name = 'billing'

urlpatterns = [
    # Dashboard
    path('',                             views.dashboard,              name='dashboard'),

    # Invoice
    path('invoices/',                   views.invoice_list,   name='invoice_list'),
    path('invoices/create/',            views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/',          views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/',     views.invoice_update, name='invoice_update'),
    path('invoices/<int:pk>/pdf/',      pdf_views.invoice_pdf, name='invoice_pdf'),
    # Alias: singular form for compatibility
    path('invoice/<int:pk>/pdf/',       pdf_views.invoice_pdf, name='invoice_pdf_alt'),

    # Payment
    path('payments/create/',            views.payment_create, name='payment_create'),
    path('payments/<int:pk>/edit/',     views.payment_update, name='payment_update'),
    path('invoices/<int:invoice_pk>/payments/', views.payment_list, name='payment_list'),

    # InsurancePolicy
    path('insurance/',                       views.insurance_policy_list,   name='insurance_policy_list'),
    path('insurance/create/',                views.insurance_policy_create, name='insurance_policy_create'),
    path('insurance/<int:pk>/',              views.insurance_policy_detail, name='insurance_policy_detail'),
    path('insurance/<int:pk>/edit/',         views.insurance_policy_update, name='insurance_policy_update'),

    # FinanceLoan
    path('loans/',                      views.loan_list,      name='loan_list'),
    path('loans/create/',               views.loan_create,    name='loan_create'),
    path('loans/<int:pk>/',             views.loan_detail,    name='loan_detail'),
    path('loans/<int:pk>/edit/',        views.loan_update,    name='loan_update'),

    # Service Invoice PDF
    path('service-invoice/<int:job_card_id>/pdf/', pdf_views.service_invoice_pdf, name='service_invoice_pdf'),

    # GAP 3 — Daily Collection Report
    path('daily-report/', views.daily_collection_report, name='daily_collection_report'),

    # GAP 16 — Payment Reconciliation
    path('reconciliation/', views.payment_reconciliation, name='payment_reconciliation'),

    # GAP 17 — Search Invoices
    path('search/', views.invoice_search, name='invoice_search'),

    # GAP 18 — Refunds & Advances
    path('refunds-advances/', views.refund_advance_list, name='refund_advance_list'),
    path('refunds-advances/create/', views.refund_advance_create, name='refund_advance_create'),
    path('refunds-advances/<int:pk>/', views.refund_advance_detail, name='refund_advance_detail'),

    # GAP 25 — Journal & General Ledger
    path('journal/', views.journal_entry_list, name='journal_entry_list'),
    path('journal/create/', views.journal_entry_create, name='journal_entry_create'),
    path('journal/<int:pk>/', views.journal_entry_detail, name='journal_entry_detail'),
    path('ledger/', views.general_ledger, name='general_ledger'),

    # GAP 27 — Payment Receipt PDF
    path('payment/<int:pk>/receipt/', pdf_views.payment_receipt_pdf, name='payment_receipt_pdf'),
]
